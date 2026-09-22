"""
Phase 7E: Shelf Reconstruction Engine
=====================================
Converts raw YOLO bounding boxes + Metric Learning SKU predictions
into a 2D logical layout (Shelves and Positions).

Algorithm:
1. Groups detections by source image.
2. Calculates center_y and center_x for each bounding box.
3. Uses DBSCAN on center_y to dynamically cluster rows without hardcoding.
4. Orders shelves Top-to-Bottom (lowest center_y = Shelf 1).
5. Orders products Left-to-Right (lowest center_x = Position 1).

Usage:
    python Shelf_Reconstruction/phase7e_reconstruction.py
"""

import json
from pathlib import Path
import numpy as np
from sklearn.cluster import DBSCAN

BASE_DIR = Path(__file__).parent.parent
YOLO_RESULTS = BASE_DIR / "outputs" / "retrieval_metric" / "yolo_recognition_results.json"
OUTPUT_DIR = BASE_DIR / "outputs" / "actual_shelf"

Y_CLUSTER_EPS_RATIO = 0.4 # Configurable fraction of average bounding box height for DBSCAN epsilon

def reconstruct_shelves():
    if not YOLO_RESULTS.exists():
        raise FileNotFoundError(f"Missing input: {YOLO_RESULTS}")
        
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(YOLO_RESULTS, 'r') as f:
        detections = json.load(f)
        
    # Group by image
    images_map = {}
    for det in detections:
        img_id = det["shelf_image"]
        if img_id not in images_map:
            images_map[img_id] = []
        images_map[img_id].append(det)
        
    print(f"Loaded {len(detections)} detections across {len(images_map)} images.")
    
    # Process each image
    for img_id, dets in images_map.items():
        boxes = []
        for det in dets:
            x1, y1, x2, y2 = det["bbox"]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            height = y2 - y1
            
            # Prefer predicted_sku_id if available, fallback to category mapping for Phase 6 prototype compatibility
            sku_id = det.get("predicted_sku_id", f"SKU_{det.get('predicted_category', 0):03d}")
            
            boxes.append({
                "raw_det": det,
                "center_x": center_x,
                "center_y": center_y,
                "height": height,
                "sku_id": sku_id,
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "detection_confidence": det.get("detection_confidence", 1.0),
                "recognition_similarity": det.get("top1_similarity", 1.0),
                "recognition_margin": det.get("margin", 0.0)
            })
            
        if not boxes:
            continue
            
        # Dynamic DBSCAN clustering based on average bounding box height
        avg_height = np.mean([b["height"] for b in boxes])
        y_coords = np.array([[b["center_y"]] for b in boxes])
        
        clustering = DBSCAN(eps=avg_height * Y_CLUSTER_EPS_RATIO, min_samples=1).fit(y_coords)
        
        # Group boxes into clusters
        clusters = {}
        for box, label in zip(boxes, clustering.labels_):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(box)
            
        # Order clusters top-to-bottom (min mean center_y first)
        cluster_means = []
        for label, c_boxes in clusters.items():
            mean_y = np.mean([b["center_y"] for b in c_boxes])
            cluster_means.append((label, mean_y, c_boxes))
            
        cluster_means.sort(key=lambda x: x[1]) # Sort ASC by Y (Top is y=0)
        
        shelves_output = []
        
        # Build logical schema
        for shelf_idx, (label, mean_y, c_boxes) in enumerate(cluster_means, start=1):
            # Sort boxes left-to-right
            c_boxes.sort(key=lambda b: b["center_x"])
            
            products_output = []
            for pos_idx, b in enumerate(c_boxes, start=1):
                products_output.append({
                    "position": pos_idx,
                    "sku_id": b["sku_id"],
                    "detection_confidence": round(b["detection_confidence"], 4),
                    "recognition_similarity": round(b["recognition_similarity"], 4),
                    "recognition_margin": round(b["recognition_margin"], 4),
                    "center_x": round(b["center_x"], 2),
                    "center_y": round(b["center_y"], 2),
                    "bbox": b["bbox"]
                })
                
            shelves_output.append({
                "shelf_id": shelf_idx,
                "products": products_output
            })
            
        audit_id = f"AUDIT_{img_id.replace('.JPG', '')}"
        
        actual_shelf_json = {
            "audit_id": audit_id,
            "image_id": img_id,
            "model_version": "resnet50_triplet_v1",
            "shelves": shelves_output
        }
        
        out_path = OUTPUT_DIR / f"{audit_id}.json"
        with open(out_path, 'w') as f:
            json.dump(actual_shelf_json, f, indent=2)
            
    print(f"✅ Reconstructed {len(images_map)} actual shelf JSONs into {OUTPUT_DIR}")


if __name__ == "__main__":
    print("=" * 60)
    print(" PHASE 7E: SHELF RECONSTRUCTION (Physical → Logical)")
    print("=" * 60)
    reconstruct_shelves()
