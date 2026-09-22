"""
Phase 4: YOLO-Based Product Detection — Training
=================================================
Trains a YOLOv8n (nano) model on the prepared grocery dataset.

Model choice:
    YOLOv8n is the smallest variant — fast to train, good baseline.
    With only 166 training images, a larger model would overfit.

Training strategy:
    - Transfer learning from COCO-pretrained weights
    - 100 epochs with early stopping (patience=20)
    - Apple Silicon MPS acceleration (if available)
    - Image size 640 (YOLO default)

Usage:
    python phase4_train_yolo.py
"""

from pathlib import Path
from ultralytics import YOLO


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATA_YAML = BASE_DIR / "dataset_yolo" / "data.yaml"
PROJECT_DIR = BASE_DIR / "runs"
EXPERIMENT_NAME = "grocery_baseline"

# Training hyperparameters
MODEL_VARIANT = "yolov8n.pt"     # nano — smallest, fastest
EPOCHS = 100                      # max epochs (early stopping may cut short)
PATIENCE = 20                     # stop if no improvement for 20 epochs
IMG_SIZE = 640                    # standard YOLO input size
BATCH_SIZE = 16                   # batch size (auto-adjusted if GPU memory insufficient)


# ──────────────────────────────────────────────
# Training
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 4: YOLO-BASED PRODUCT DETECTION — TRAINING")
    print("=" * 70)

    # Verify data.yaml exists
    if not DATA_YAML.exists():
        print(f"\n  ❌ data.yaml not found at: {DATA_YAML}")
        print("  Run convert_to_yolo.py first (Phase 3B)")
        return

    print(f"\n  Model:      {MODEL_VARIANT}")
    print(f"  Data:       {DATA_YAML}")
    print(f"  Epochs:     {EPOCHS} (early stopping patience={PATIENCE})")
    print(f"  Image size: {IMG_SIZE}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Output:     {PROJECT_DIR / EXPERIMENT_NAME}")

    # Load pretrained YOLOv8n
    print("\n📦 Loading pretrained YOLOv8n...")
    model = YOLO(MODEL_VARIANT)

    # Train
    print("\n🚀 Starting training...\n")
    results = model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        patience=PATIENCE,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        project=str(PROJECT_DIR),
        name=EXPERIMENT_NAME,
        exist_ok=True,           # overwrite previous run with same name
        pretrained=True,         # use COCO pretrained weights
        verbose=True,
        plots=True,              # generate training plots
        save=True,               # save checkpoints
        save_period=-1,          # only save best and last (not every N epochs)
    )

    # Summary
    print("\n" + "=" * 70)
    print("  ✅ TRAINING COMPLETE!")
    print("=" * 70)

    results_dir = PROJECT_DIR / EXPERIMENT_NAME
    print(f"\n  Results saved to: {results_dir}")
    print(f"  Best model:       {results_dir / 'weights' / 'best.pt'}")
    print(f"  Last model:       {results_dir / 'weights' / 'last.pt'}")
    print(f"\n  Training plots:")
    print(f"    - {results_dir / 'results.png'}")
    print(f"    - {results_dir / 'confusion_matrix.png'}")
    print(f"    - {results_dir / 'F1_curve.png'}")
    print(f"    - {results_dir / 'PR_curve.png'}")


if __name__ == "__main__":
    main()
