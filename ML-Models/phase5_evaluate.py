"""
Phase 5: Model Evaluation
=========================
Evaluates the trained YOLOv8 model on the test set (P07, P08).

Reports:
    - Overall metrics: mAP50, mAP50-95, Precision, Recall
    - Per-class AP (especially minority classes Cat-3, Cat-9, Cat-10)
    - Visualizes predictions on sample test images
    - Compares ground truth vs predictions side-by-side

Usage:
    python phase5_evaluate.py
"""

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from ultralytics import YOLO


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATA_YAML = BASE_DIR / "dataset_yolo" / "data.yaml"
MODEL_PATH = BASE_DIR / "runs" / "grocery_baseline" / "weights" / "best.pt"
OUTPUT_DIR = BASE_DIR / "outputs" / "evaluation"
TEST_IMAGES_DIR = BASE_DIR / "dataset_yolo" / "images" / "test"
TEST_LABELS_DIR = BASE_DIR / "dataset_yolo" / "labels" / "test"

CLASS_NAMES = {
    0: 'Cat-1',  1: 'Cat-2',  2: 'Cat-3',  3: 'Cat-4',  4: 'Cat-5',
    5: 'Cat-6',  6: 'Cat-7',  7: 'Cat-8',  8: 'Cat-9',  9: 'Cat-10',
}

CATEGORY_COLORS_BGR = {
    0: (0, 255, 0),       # Green
    1: (255, 0, 0),       # Blue
    2: (0, 0, 255),       # Red
    3: (255, 255, 0),     # Cyan
    4: (0, 255, 255),     # Yellow
    5: (255, 0, 255),     # Magenta
    6: (128, 255, 0),     # Lime
    7: (0, 128, 255),     # Orange
    8: (255, 128, 0),     # Sky Blue
    9: (128, 0, 255),     # Purple
}


# ──────────────────────────────────────────────
# Step 1: Run official YOLO validation on test set
# ──────────────────────────────────────────────

def run_test_validation(model):
    """Run YOLO val() on the test split and return metrics."""
    print("\n📊 Running validation on test set...")

    results = model.val(
        data=str(DATA_YAML),
        split='test',
        imgsz=640,
        batch=16,
        verbose=True,
        plots=True,
        project=str(OUTPUT_DIR),
        name='test_metrics',
        exist_ok=True,
    )

    return results


# ──────────────────────────────────────────────
# Step 2: Print per-class metrics
# ──────────────────────────────────────────────

def print_per_class_metrics(results):
    """Extract and print per-class AP, precision, recall."""

    print("\n" + "=" * 80)
    print("  PER-CLASS METRICS (Test Set)")
    print("=" * 80)

    # Access the metrics
    box = results.box

    # Per-class AP50
    ap50_per_class = box.ap50          # shape: (num_classes,)
    ap50_95_per_class = box.ap         # shape: (num_classes,)
    precision_per_class = box.p        # shape: (num_classes,)
    recall_per_class = box.r           # shape: (num_classes,)

    print(f"\n  {'Class':<10} {'Precision':>10} {'Recall':>10} {'AP@50':>10} {'AP@50-95':>10}")
    print(f"  {'─────':<10} {'─────────':>10} {'──────':>10} {'─────':>10} {'────────':>10}")

    for i in range(len(ap50_per_class)):
        name = CLASS_NAMES.get(i, f'Class-{i}')
        p = precision_per_class[i]
        r = recall_per_class[i]
        ap50 = ap50_per_class[i]
        ap = ap50_95_per_class[i]
        print(f"  {name:<10} {p:>10.4f} {r:>10.4f} {ap50:>10.4f} {ap:>10.4f}")

    # Overall
    print(f"  {'─' * 52}")
    print(f"  {'ALL':<10} {box.mp:>10.4f} {box.mr:>10.4f} {box.map50:>10.4f} {box.map:>10.4f}")

    return {
        'map50': box.map50,
        'map50_95': box.map,
        'precision': box.mp,
        'recall': box.mr,
    }


# ──────────────────────────────────────────────
# Step 3: Visualize predictions on test images
# ──────────────────────────────────────────────

def draw_ground_truth(image, label_path):
    """Draw ground truth boxes on image (green dashed-style)."""
    img = image.copy()
    h_img, w_img = img.shape[:2]

    if not label_path.exists():
        return img

    with open(label_path, 'r') as f:
        lines = f.readlines()

    scale_factor = max(w_img, h_img) / 1500.0
    thickness = max(2, int(2 * scale_factor))
    font_scale = max(0.4, 0.4 * scale_factor)

    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:
            continue

        class_id = int(parts[0])
        cx, cy, norm_w, norm_h = map(float, parts[1:])

        # Un-normalize
        w = norm_w * w_img
        h = norm_h * h_img
        x = int((cx * w_img) - (w / 2))
        y = int((cy * h_img) - (h / 2))
        w, h = int(w), int(h)

        color = CATEGORY_COLORS_BGR.get(class_id, (255, 255, 255))
        label = f"GT:{CLASS_NAMES.get(class_id, str(class_id))}"

        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)

        (text_w, text_h), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y = max(y - 4, text_h + 4)
        cv2.rectangle(img, (x, label_y - text_h - 4),
                      (x + text_w + 4, label_y + 2), color, -1)
        cv2.putText(img, label, (x + 2, label_y - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA)

    return img


def draw_predictions(image, results):
    """Draw predicted boxes on image."""
    img = image.copy()
    h_img, w_img = img.shape[:2]

    scale_factor = max(w_img, h_img) / 1500.0
    thickness = max(2, int(2 * scale_factor))
    font_scale = max(0.4, 0.4 * scale_factor)

    boxes = results[0].boxes
    for box in boxes:
        cls = int(box.cls.item())
        conf = float(box.conf.item())
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        color = CATEGORY_COLORS_BGR.get(cls, (255, 255, 255))
        label = f"{CLASS_NAMES.get(cls, str(cls))} {conf:.2f}"

        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        (text_w, text_h), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y = max(y1 - 4, text_h + 4)
        cv2.rectangle(img, (x1, label_y - text_h - 4),
                      (x1 + text_w + 4, label_y + 2), color, -1)
        cv2.putText(img, label, (x1 + 2, label_y - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA)

    return img


def create_comparison_gallery(model, n_samples=6):
    """Create side-by-side ground truth vs prediction comparison."""
    print("\n🖼️  Creating prediction comparison gallery...")

    test_images = sorted(TEST_IMAGES_DIR.glob('*.JPG'))
    if not test_images:
        print("  ⚠ No test images found!")
        return

    # Select evenly spaced samples
    step = max(1, len(test_images) // n_samples)
    samples = test_images[::step][:n_samples]

    fig, axes = plt.subplots(n_samples, 2, figsize=(20, 5 * n_samples))
    fig.suptitle('Phase 5: Ground Truth (left) vs Predictions (right)',
                 fontsize=16, fontweight='bold', y=0.99)

    for idx, img_path in enumerate(samples):
        # Read image
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        # Ground truth
        lbl_path = TEST_LABELS_DIR / (img_path.stem + '.txt')
        gt_img = draw_ground_truth(img, lbl_path)

        # Predictions
        pred_results = model.predict(
            str(img_path), imgsz=640, conf=0.25, verbose=False
        )
        pred_img = draw_predictions(img, pred_results)

        # Count detections
        n_gt = 0
        if lbl_path.exists():
            with open(lbl_path) as f:
                n_gt = len(f.readlines())
        n_pred = len(pred_results[0].boxes)

        # Plot
        ax_gt = axes[idx, 0] if n_samples > 1 else axes[0]
        ax_pred = axes[idx, 1] if n_samples > 1 else axes[1]

        ax_gt.imshow(cv2.cvtColor(gt_img, cv2.COLOR_BGR2RGB))
        ax_gt.set_title(f"Ground Truth: {img_path.stem} ({n_gt} boxes)", fontsize=9)
        ax_gt.axis('off')

        ax_pred.imshow(cv2.cvtColor(pred_img, cv2.COLOR_BGR2RGB))
        ax_pred.set_title(f"Predictions: {img_path.stem} ({n_pred} boxes)", fontsize=9)
        ax_pred.axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    gallery_path = OUTPUT_DIR / "gt_vs_predictions.png"
    plt.savefig(str(gallery_path), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {gallery_path}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 5: MODEL EVALUATION")
    print("=" * 70)

    # Check model exists
    if not MODEL_PATH.exists():
        print(f"\n  ❌ Model not found: {MODEL_PATH}")
        print("  Run phase4_train_yolo.py first")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load trained model
    print(f"\n📦 Loading model: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    # Step 1: Official validation on test set
    results = run_test_validation(model)

    # Step 2: Per-class metrics
    overall = print_per_class_metrics(results)

    # Step 3: Visual comparison
    create_comparison_gallery(model, n_samples=6)

    # Final summary
    print("\n" + "=" * 70)
    print("  ✅ EVALUATION COMPLETE!")
    print("=" * 70)
    print(f"\n  Overall Test Metrics:")
    print(f"    mAP@50:    {overall['map50']:.4f}")
    print(f"    mAP@50-95: {overall['map50_95']:.4f}")
    print(f"    Precision:  {overall['precision']:.4f}")
    print(f"    Recall:     {overall['recall']:.4f}")
    print(f"\n  Output files:")
    print(f"    {OUTPUT_DIR / 'gt_vs_predictions.png'}")
    print(f"    {OUTPUT_DIR / 'test_metrics/'}")


if __name__ == "__main__":
    main()
