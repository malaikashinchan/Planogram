"""
Phase 6D+6E — ResNet50 Embedding Extraction & Reference Index
==============================================================
Extracts visual embeddings from:
    1. All 3,702 catalogue reference images (ProductImages) → reference index
    2. All 2,495 YOLO-detected shelf crops → query embeddings

Uses pretrained ResNet50 (ImageNet) as a feature extractor.
We do NOT train ResNet50 — we use it purely as a frozen backbone.

The output of ResNet50's avgpool layer is a 2048-dim vector.
We L2-normalize all embeddings so cosine similarity = dot product.

Usage:
    python phase6de_embeddings.py
"""

import cv2
import json
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path
from collections import defaultdict
import time


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
CATALOGUE_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part1" / "ProductImages"
CROPS_DIR = BASE_DIR / "outputs" / "yolo_crops"
MANIFEST_PATH = CROPS_DIR / "detections_manifest.json"
OUTPUT_DIR = BASE_DIR / "outputs" / "embeddings"

# Device
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# Image preprocessing — standard ImageNet normalization
TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

BATCH_SIZE = 64


# ──────────────────────────────────────────────
# Build the feature extractor
# ──────────────────────────────────────────────

def build_feature_extractor():
    """
    Load pretrained ResNet50 and remove the final classification layer.
    Output: 2048-dim feature vector per image.
    """
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)

    # Remove the final FC layer — we want the avgpool output (2048-dim)
    model = nn.Sequential(*list(model.children())[:-1])

    model.eval()
    model.to(DEVICE)

    print(f"  ResNet50 feature extractor loaded on {DEVICE}")
    print(f"  Output: 2048-dim embedding per image")

    return model


# ──────────────────────────────────────────────
# Batch embedding extraction
# ──────────────────────────────────────────────

def extract_embeddings_batch(model, image_paths, desc=""):
    """
    Extract L2-normalized embeddings for a list of image paths.

    Returns:
        embeddings: np.ndarray of shape (N, 2048), L2-normalized
        valid_paths: list of paths that were successfully processed
    """
    all_embeddings = []
    valid_paths = []
    failed = 0

    total = len(image_paths)
    print(f"\n  Extracting embeddings: {desc} ({total} images)")

    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch_paths = image_paths[batch_start:batch_end]

        # Load and preprocess batch
        batch_tensors = []
        batch_valid_paths = []

        for p in batch_paths:
            img = cv2.imread(str(p))
            if img is None:
                failed += 1
                continue

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            try:
                tensor = TRANSFORM(img_rgb)
                batch_tensors.append(tensor)
                batch_valid_paths.append(p)
            except Exception:
                failed += 1
                continue

        if not batch_tensors:
            continue

        # Stack into batch and run inference
        batch_input = torch.stack(batch_tensors).to(DEVICE)

        with torch.no_grad():
            features = model(batch_input)         # (B, 2048, 1, 1)
            features = features.squeeze(-1).squeeze(-1)  # (B, 2048)

            # L2 normalize
            features = nn.functional.normalize(features, p=2, dim=1)

        all_embeddings.append(features.cpu().numpy())
        valid_paths.extend(batch_valid_paths)

        # Progress
        processed = min(batch_end, total)
        if processed % (BATCH_SIZE * 5) == 0 or processed == total:
            print(f"    {processed}/{total} images processed...")

    if not all_embeddings:
        return np.array([]), []

    embeddings = np.vstack(all_embeddings)

    if failed > 0:
        print(f"    ⚠ {failed} images failed to load")
    print(f"    ✅ {len(valid_paths)} embeddings extracted, shape: {embeddings.shape}")

    return embeddings, valid_paths


# ──────────────────────────────────────────────
# Step 1: Build reference catalogue index
# ──────────────────────────────────────────────

def build_reference_index(model):
    """
    Extract embeddings for all 3,702 catalogue reference images.
    Save as a structured index mapping each embedding to its SKU.
    """
    print("\n" + "─" * 70)
    print("  STEP 1: BUILD REFERENCE CATALOGUE INDEX")
    print("─" * 70)

    # Collect all reference images with their category/brand labels
    ref_paths = []
    ref_labels = []

    for cat_id in range(1, 11):
        cat_dir = CATALOGUE_DIR / str(cat_id)
        if not cat_dir.exists():
            continue

        files = sorted(cat_dir.glob('*.jpg'))
        for f in files:
            ref_paths.append(f)
            ref_labels.append({
                "category": cat_id,
                "brand_id": f"B{cat_id}",
                "sku_id": f"SKU_{cat_id:03d}",
                "filename": f.name,
            })

    print(f"  Total reference images: {len(ref_paths)}")

    # Extract embeddings
    embeddings, valid_paths = extract_embeddings_batch(
        model, ref_paths, desc="Catalogue references"
    )

    # Build label index (only for successfully loaded images)
    valid_labels = []
    path_set = set(str(p) for p in valid_paths)
    for path, label in zip(ref_paths, ref_labels):
        if str(path) in path_set:
            valid_labels.append(label)

    # Save
    np.save(str(OUTPUT_DIR / "reference_embeddings.npy"), embeddings)

    with open(OUTPUT_DIR / "reference_labels.json", 'w') as f:
        json.dump(valid_labels, f, indent=2)

    print(f"\n  Saved: reference_embeddings.npy ({embeddings.shape})")
    print(f"  Saved: reference_labels.json ({len(valid_labels)} entries)")

    # Print distribution
    from collections import Counter
    cat_counts = Counter(l['category'] for l in valid_labels)
    print(f"\n  {'Category':<12} {'SKU':<12} {'References':>12}")
    print(f"  {'────────':<12} {'───':<12} {'──────────':>12}")
    for cat_id in range(1, 11):
        print(f"  Cat-{cat_id:<7} SKU_{cat_id:03d}    {cat_counts.get(cat_id, 0):>12}")

    return embeddings, valid_labels


# ──────────────────────────────────────────────
# Step 2: Extract crop embeddings
# ──────────────────────────────────────────────

def extract_crop_embeddings(model):
    """
    Extract embeddings for all YOLO-detected shelf crops.
    """
    print("\n" + "─" * 70)
    print("  STEP 2: EXTRACT SHELF CROP EMBEDDINGS")
    print("─" * 70)

    # Load manifest
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    print(f"  Total crops in manifest: {len(manifest)}")

    # Resolve crop paths
    crop_paths = []
    for det in manifest:
        crop_path = CROPS_DIR / det['crop_path']
        crop_paths.append(crop_path)

    # Extract embeddings
    embeddings, valid_paths = extract_embeddings_batch(
        model, crop_paths, desc="YOLO shelf crops"
    )

    # Save
    np.save(str(OUTPUT_DIR / "crop_embeddings.npy"), embeddings)

    # Save a filtered manifest (only valid crops)
    valid_path_set = set(str(p) for p in valid_paths)
    valid_manifest = [
        det for det, cp in zip(manifest, crop_paths)
        if str(cp) in valid_path_set
    ]

    with open(OUTPUT_DIR / "crop_manifest.json", 'w') as f:
        json.dump(valid_manifest, f, indent=2)

    print(f"\n  Saved: crop_embeddings.npy ({embeddings.shape})")
    print(f"  Saved: crop_manifest.json ({len(valid_manifest)} entries)")

    return embeddings, valid_manifest


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 6D+6E: RESNET50 EMBEDDING EXTRACTION & REFERENCE INDEX")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build feature extractor
    print("\n📦 Building ResNet50 feature extractor...")
    model = build_feature_extractor()

    start_time = time.time()

    # Step 1: Reference catalogue
    ref_embeddings, ref_labels = build_reference_index(model)

    # Step 2: Crop embeddings
    crop_embeddings, crop_manifest = extract_crop_embeddings(model)

    elapsed = time.time() - start_time

    # Final summary
    print("\n" + "=" * 70)
    print("  ✅ PHASE 6D+6E COMPLETE!")
    print("=" * 70)
    print(f"\n  Reference index: {ref_embeddings.shape[0]} images × {ref_embeddings.shape[1]} dims")
    print(f"  Crop embeddings: {crop_embeddings.shape[0]} crops × {crop_embeddings.shape[1]} dims")
    print(f"  Elapsed time:    {elapsed:.1f}s")
    print(f"\n  Output: {OUTPUT_DIR}")
    print(f"    reference_embeddings.npy")
    print(f"    reference_labels.json")
    print(f"    crop_embeddings.npy")
    print(f"    crop_manifest.json")


if __name__ == "__main__":
    main()
