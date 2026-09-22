"""
Phase 6C — Generate YOLO Product Crops
=======================================
Runs YOLO inference on shelf images and crops each detected product.

For every detection we produce:
    - A cropped .jpg image
    - A JSON manifest entry preserving the full detection chain:
        shelf_image → YOLO bbox → crop → (later) SKU recognition

We process ALL shelf images (train + val + test splits) because:
    - The embedding pipeline needs crops from known-identity images for evaluation
    - The shelf crops from ProductImagesFromShelves already have ground truth labels

Usage:
    python phase6c_generate_crops.py
"""

import cv2
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "runs" / "grocery_baseline" / "weights" / "best.pt"
OUTPUT_DIR = BASE_DIR / "outputs" / "yolo_crops"

# Process all three splits
SPLITS = ['train', 'val', 'test']
IMAGES_DIR = BASE_DIR / "dataset_yolo" / "images"

# YOLO class to brand mapping (from Phase 6B.5 audit)
CLASS_TO_BRAND = {
    0: {"sku_id": "SKU_001", "brand": "Marlboro"},
    1: {"sku_id": "SKU_002", "brand": "Kent"},
    2: {"sku_id": "SKU_003", "brand": "LM"},
    3: {"sku_id": "SKU_004", "brand": "Parliament"},
    4: {"sku_id": "SKU_005", "brand": "Pall Mall"},
    5: {"sku_id": "SKU_006", "brand": "Camel"},
    6: {"sku_id": "SKU_007", "brand": "Winston"},
    7: {"sku_id": "SKU_008", "brand": "Lucky Strike"},
    8: {"sku_id": "SKU_009", "brand": "Muratti"},
    9: {"sku_id": "SKU_010", "brand": "Tekel"},
}

# Confidence threshold for keeping detections
CONF_THRESHOLD = 0.25


# ──────────────────────────────────────────────
# Crop extraction
# ──────────────────────────────────────────────

def extract_crops(model, split):
    """
    Run YOLO on all images in a split and extract product crops.
    
    Returns:
        list of detection dicts
    """
    split_dir = IMAGES_DIR / split
    if not split_dir.exists():
        print(f"  ⚠ Split directory not found: {split_dir}")
        return []

    images = sorted(split_dir.glob('*.JPG'))
    print(f"\n  [{split.upper()}] Processing {len(images)} images...")

    crop_dir = OUTPUT_DIR / "crops" / split
    crop_dir.mkdir(parents=True, exist_ok=True)

    detections = []
    det_id = 0

    for img_idx, img_path in enumerate(images):
        # Run YOLO inference
        results = model.predict(
            str(img_path),
            imgsz=640,
            conf=CONF_THRESHOLD,
            verbose=False,
        )

        # Read original image for cropping (full resolution)
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"    ⚠ Could not read: {img_path.name}")
            continue

        img_h, img_w = img.shape[:2]
        boxes = results[0].boxes

        for box in boxes:
            cls = int(box.cls.item())
            conf = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # Clamp to image bounds
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(img_w, int(x2))
            y2 = min(img_h, int(y2))

            # Skip tiny crops
            crop_w = x2 - x1
            crop_h = y2 - y1
            if crop_w < 10 or crop_h < 10:
                continue

            # Extract crop
            crop = img[y1:y2, x1:x2]

            # Generate unique detection ID
            det_id_str = f"{split}_{img_path.stem}_det{det_id:04d}"
            crop_filename = f"{det_id_str}.jpg"
            crop_path = crop_dir / crop_filename

            # Save crop
            cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Build detection record
            brand_info = CLASS_TO_BRAND.get(cls, {"sku_id": "UNKNOWN", "brand": "Unknown"})

            detection = {
                "detection_id": det_id_str,
                "shelf_image": img_path.name,
                "split": split,
                "yolo_class": cls,
                "yolo_category": f"Cat-{cls + 1}",
                "detection_confidence": round(conf, 4),
                "bbox": [x1, y1, x2, y2],
                "crop_width": crop_w,
                "crop_height": crop_h,
                "crop_path": str(crop_path.relative_to(OUTPUT_DIR)),
                "brand_info": brand_info,
            }
            detections.append(detection)
            det_id += 1

        if (img_idx + 1) % 50 == 0:
            print(f"    Processed {img_idx + 1}/{len(images)} images, "
                  f"{det_id} crops so far...")

    print(f"    ✅ {split}: {len(images)} images → {len(detections)} crops extracted")
    return detections


# ──────────────────────────────────────────────
# Summary statistics
# ──────────────────────────────────────────────

def print_summary(all_detections):
    """Print crop extraction summary."""
    from collections import Counter

    print("\n" + "=" * 70)
    print("  CROP EXTRACTION SUMMARY")
    print("=" * 70)

    # By split
    split_counts = Counter(d['split'] for d in all_detections)
    print(f"\n  {'Split':<10} {'Crops':>10}")
    print(f"  {'─────':<10} {'─────':>10}")
    for split in SPLITS:
        print(f"  {split:<10} {split_counts.get(split, 0):>10}")
    print(f"  {'TOTAL':<10} {len(all_detections):>10}")

    # By category
    cat_counts = Counter(d['yolo_category'] for d in all_detections)
    print(f"\n  {'Category':<12} {'Brand':<15} {'Crops':>8}")
    print(f"  {'────────':<12} {'─────':<15} {'─────':>8}")
    for cls_id in range(10):
        cat = f"Cat-{cls_id + 1}"
        brand = CLASS_TO_BRAND[cls_id]['brand']
        print(f"  {cat:<12} {brand:<15} {cat_counts.get(cat, 0):>8}")

    # Confidence distribution
    confs = [d['detection_confidence'] for d in all_detections]
    print(f"\n  Confidence distribution:")
    print(f"    Min:    {min(confs):.4f}")
    print(f"    Max:    {max(confs):.4f}")
    print(f"    Mean:   {np.mean(confs):.4f}")
    print(f"    Median: {np.median(confs):.4f}")

    # Crop size distribution
    widths = [d['crop_width'] for d in all_detections]
    heights = [d['crop_height'] for d in all_detections]
    print(f"\n  Crop size distribution:")
    print(f"    Width:  {min(widths)}–{max(widths)} px (mean {np.mean(widths):.0f})")
    print(f"    Height: {min(heights)}–{max(heights)} px (mean {np.mean(heights):.0f})")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 6C: GENERATE YOLO PRODUCT CROPS")
    print("=" * 70)

    # Check model
    if not MODEL_PATH.exists():
        print(f"\n  ❌ Model not found: {MODEL_PATH}")
        print("  Run phase4_train_yolo.py first")
        return

    # Clean output directory
    import shutil
    if OUTPUT_DIR.exists():
        print(f"\n  🧹 Cleaning old output: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load model
    print(f"\n📦 Loading YOLO model: {MODEL_PATH.name}")
    model = YOLO(str(MODEL_PATH))

    # Extract crops from all splits
    all_detections = []
    for split in SPLITS:
        detections = extract_crops(model, split)
        all_detections.extend(detections)

    # Save manifest
    manifest_path = OUTPUT_DIR / "detections_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(all_detections, f, indent=2)
    print(f"\n📝 Manifest saved: {manifest_path}")
    print(f"   {len(all_detections)} total detections")

    # Summary
    print_summary(all_detections)

    print("\n" + "=" * 70)
    print("  ✅ PHASE 6C COMPLETE!")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
