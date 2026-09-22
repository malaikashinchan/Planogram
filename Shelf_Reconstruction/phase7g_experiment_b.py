"""
Phase 7G: Experiment B - End-to-End ML Pipeline Evaluation
==========================================================
1. Parses original Ground Truth crop filenames to extract true bounding boxes.
2. Reconstructs them into GT Ideal Planograms using our Phase 7E DBSCAN logic.
3. Compares the YOLO+ResNet Actual Shelf JSONs against these GT Ideal Planograms
   using our Phase 7F Comparison Engine.
4. Computes massive dataset-wide compliance metrics.
"""

import json
from pathlib import Path
import os
import numpy as np
from sklearn.cluster import DBSCAN

# Import the exact comparison logic we just finalized
import sys
sys.path.append(str(Path(__file__).parent))
from phase7f_comparison import compare_planograms

BASE_DIR = Path(__file__).parent.parent
PRODUCT_CROPS_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part2" / "ProductImagesFromShelves"
ACTUAL_SHELF_DIR = BASE_DIR / "outputs" / "actual_shelf"

Y_CLUSTER_EPS_RATIO = 0.4

def extract_ground_truth_boxes():
    """Extracts all ground truth boxes from crop filenames and groups by image."""
    gt_by_image = {}
    
    for cat_id in range(1, 11):
        cat_dir = PRODUCT_CROPS_DIR / str(cat_id)
        if not cat_dir.exists():
            continue
            
        for fname in os.listdir(cat_dir):
            if not fname.endswith('.png'):
                continue
                
            # Example: C1_P01_N1_S2_1.JPG_1084_816_208_48.png
            parts = fname.replace('.png', '').split('_')
            
            # Find where the extension .JPG/.jpg is to split the filename
            img_name = None
            for i, p in enumerate(parts):
                if p.upper().endswith('JPG'):
                    img_name = "_".join(parts[:i+1])
                    coords = parts[i+1:]
                    break
                    
            if not img_name or len(coords) < 4:
                continue
                
            x, y, w, h = map(int, coords[:4])
            center_x = x + (w / 2)
            center_y = y + (h / 2)
            
            if img_name not in gt_by_image:
                gt_by_image[img_name] = []
                
            gt_by_image[img_name].append({
                "sku_id": f"SKU_{cat_id:03d}",
                "center_x": center_x,
                "center_y": center_y,
                "height": h
            })
            
    return gt_by_image

def reconstruct_ideal_planogram(img_name, gt_boxes):
    """Uses the exact Phase 7E logic to cluster GT boxes into a Canonical JSON."""
    if not gt_boxes:
        return {"planogram_id": img_name, "version": 1, "store_id": "STORE_001", "shelves": []}
        
    avg_height = np.mean([b["height"] for b in gt_boxes])
    y_coords = np.array([[b["center_y"]] for b in gt_boxes])
    
    clustering = DBSCAN(eps=avg_height * Y_CLUSTER_EPS_RATIO, min_samples=1).fit(y_coords)
    
    clusters = {}
    for i, label in enumerate(clustering.labels_):
        clusters.setdefault(label, []).append(gt_boxes[i])
        
    cluster_means = [(lbl, np.mean([b["center_y"] for b in items])) for lbl, items in clusters.items()]
    cluster_means.sort(key=lambda x: x[1])
    
    shelves = []
    for shelf_idx, (lbl, _) in enumerate(cluster_means, 1):
        items = clusters[lbl]
        items.sort(key=lambda x: x["center_x"])
        
        products = []
        for pos_idx, b in enumerate(items, 1):
            products.append({
                "position": pos_idx,
                "sku_id": b["sku_id"]
            })
            
        shelves.append({
            "shelf_id": shelf_idx,
            "products": products
        })
        
    return {
        "planogram_id": img_name,
        "version": 1,
        "store_id": "STORE_001",
        "shelves": shelves
    }

if __name__ == "__main__":
    print("=" * 60)
    print(" PHASE 7G: END-TO-END DATASET COMPLIANCE EVALUATION")
    print("=" * 60)
    
    # 1. Load ML Actual Shelves
    actual_shelves = {}
    for fpath in ACTUAL_SHELF_DIR.glob("*.json"):
        with open(fpath) as f:
            data = json.load(f)
            # Map back to original image name
            img_name = data["audit_id"].replace("AUDIT_", "") + ".JPG"
            actual_shelves[img_name] = data
            
    # 2. Extract GT and Reconstruct Ideal Planograms
    gt_by_image = extract_ground_truth_boxes()
    print(f"Loaded ML outputs for {len(actual_shelves)} images.")
    print(f"Extracted GT boxes for {len(gt_by_image)} images.")
    
    total_pos_acc = []
    total_avail = []
    total_facing = []
    
    total_missing = 0
    total_extra = 0
    total_misplaced = 0
    
    matched_count = 0
    
    for img_name, actual_data in actual_shelves.items():
        if img_name not in gt_by_image:
            continue
            
        # Reconstruct GT Ideal
        ideal_data = reconstruct_ideal_planogram(img_name, gt_by_image[img_name])
        
        # Compare!
        report = compare_planograms(ideal_data, actual_data)
        
        total_pos_acc.append(report["metrics"]["position_accuracy"])
        total_avail.append(report["metrics"]["availability_rate"])
        total_facing.append(report["metrics"]["facing_compliance"])
        
        total_missing += len(report.get("missing_products", []))
        total_extra += len(report.get("extra_products", []))
        total_misplaced += len(report.get("misplaced_products", []))
        
        matched_count += 1
        
    print(f"\nSuccessfully evaluated {matched_count} images end-to-end.")
    print("\n📊 DATASET-WIDE COMPLIANCE METRICS:")
    print(f"  Average Position Accuracy : {np.mean(total_pos_acc):.1%}")
    print(f"  Average Availability Rate : {np.mean(total_avail):.1%}")
    print(f"  Average Facing Compliance : {np.mean(total_facing):.1%}")
    
    print("\n🚨 TOTAL GROSS VIOLATIONS ACROSS DATASET:")
    print(f"  Total Missing Products   : {total_missing}")
    print(f"  Total Extra Products     : {total_extra}")
    print(f"  Total Misplaced Products : {total_misplaced}")
    print("=" * 60)
