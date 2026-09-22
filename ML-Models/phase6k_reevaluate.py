"""
Phase 6K — Re-evaluate on GroceryDataset (Fine-Tuned ResNet50)
==============================================================
Runs the exact same evaluation as Phase 6F+6G+6H, but uses the
fine-tuned ResNet50 backbone (trained on Products-10K) instead of
the frozen ImageNet weights.

This script runs the entire evaluation end-to-end:
    1. Loads the fine-tuned backbone.
    2. Extracts embeddings for the 3,701 reference catalogue images.
    3. Evaluates YOLO crop retrieval (diagnostic).
    4. Evaluates GT shelf crop retrieval (primary evaluation).

Usage:
    python phase6k_reevaluate.py
"""

import cv2
import json
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
import shutil

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
FINETUNE_OUTPUT_DIR = BASE_DIR / "outputs" / "finetune"
MODEL_PATH = FINETUNE_OUTPUT_DIR / "resnet50_product10k_subset.pth"

CATALOGUE_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part1" / "ProductImages"
SHELF_CROPS_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part2" / "ProductImagesFromShelves"
YOLO_CROPS_MANIFEST = BASE_DIR / "outputs" / "yolo_crops" / "detections_manifest.json"
YOLO_CROPS_DIR = BASE_DIR / "outputs" / "yolo_crops"

OUTPUT_DIR = BASE_DIR / "outputs" / "retrieval_finetuned"

TOP_K = 5
BRAND_NAMES = {
    1: "Marlboro", 2: "Kent", 3: "LM", 4: "Parliament", 5: "Pall Mall",
    6: "Camel", 7: "Winston", 8: "Lucky Strike", 9: "Muratti", 10: "Tekel",
}
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# ──────────────────────────────────────────────
# Feature Extractor
# ──────────────────────────────────────────────

def load_finetuned_backbone():
    print("\n📦 Loading fine-tuned ResNet50 backbone...")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Fine-tuned model not found at: {MODEL_PATH}")

    # Build base model (no weights since we load our own state dict)
    model = models.resnet50(weights=None)
    backbone = nn.Sequential(*list(model.children())[:-1])
    
    # Load state dict
    state_dict = torch.load(str(MODEL_PATH), map_location=DEVICE)
    backbone.load_state_dict(state_dict)
    
    backbone.eval()
    backbone.to(DEVICE)
    print("  ✅ Fine-tuned backbone loaded successfully")
    return backbone


def extract_embeddings_batch(model, image_paths, batch_size=64, desc=""):
    all_embeddings = []
    valid_indices = []

    for batch_start in range(0, len(image_paths), batch_size):
        batch_end = min(batch_start + batch_size, len(image_paths))
        batch_paths = image_paths[batch_start:batch_end]

        tensors = []
        indices = []

        for offset, p in enumerate(batch_paths):
            img = cv2.imread(str(p))
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            try:
                tensors.append(TRANSFORM(img_rgb))
                indices.append(batch_start + offset)
            except Exception:
                continue

        if not tensors:
            continue

        batch_input = torch.stack(tensors).to(DEVICE)
        with torch.no_grad():
            features = model(batch_input).squeeze(-1).squeeze(-1)
            features = nn.functional.normalize(features, p=2, dim=1)

        all_embeddings.append(features.cpu().numpy())
        valid_indices.extend(indices)

        if batch_end % (batch_size * 5) == 0 or batch_end == len(image_paths):
            print(f"    {batch_end}/{len(image_paths)} {desc} processed...")

    if not all_embeddings:
        return np.array([]), []

    return np.vstack(all_embeddings), valid_indices


# ──────────────────────────────────────────────
# Retrieval Engine
# ──────────────────────────────────────────────

def retrieve_nearest(query_embeddings, ref_embeddings, ref_labels, top_k=5):
    sim_matrix = query_embeddings @ ref_embeddings.T

    results = []
    for i in range(sim_matrix.shape[0]):
        sims = sim_matrix[i]
        top_indices = np.argsort(sims)[::-1][:top_k]

        top_matches = []
        for idx in top_indices:
            ref = ref_labels[idx]
            top_matches.append({
                "reference": ref["filename"],
                "brand_id": f"B{ref['category']}",
                "category": ref["category"],
                "brand": BRAND_NAMES.get(ref["category"], "Unknown"),
                "similarity": float(sims[idx]),
            })

        # Max similarity per brand
        brand_best = {}
        for m in top_matches:
            cat = m["category"]
            if cat not in brand_best or m["similarity"] > brand_best[cat]:
                brand_best[cat] = m["similarity"]

        sorted_brands = sorted(brand_best.items(), key=lambda x: -x[1])
        top1_cat = sorted_brands[0][0]
        top1_sim = sorted_brands[0][1]
        top2_cat = sorted_brands[1][0] if len(sorted_brands) > 1 else None
        top2_sim = sorted_brands[1][1] if len(sorted_brands) > 1 else 0.0

        results.append({
            "predicted_category": top1_cat,
            "predicted_brand": BRAND_NAMES.get(top1_cat, "Unknown"),
            "top1_similarity": float(top1_sim),
            "top2_category": top2_cat,
            "top2_brand": BRAND_NAMES.get(top2_cat, "Unknown") if top2_cat else None,
            "top2_similarity": float(top2_sim),
            "margin": float(top1_sim - top2_sim),
            "top_matches": top_matches,
        })
    return results


def plot_metrics(correct_sims, incorrect_sims, per_class, save_prefix):
    # Plot 1: Similarities
    fig, ax = plt.subplots(figsize=(8, 5))
    if correct_sims:
        ax.hist(correct_sims, bins=40, alpha=0.7, label=f'Correct ({len(correct_sims)})', color='#2ecc71', edgecolor='#27ae60')
    if incorrect_sims:
        ax.hist(incorrect_sims, bins=40, alpha=0.7, label=f'Incorrect ({len(incorrect_sims)})', color='#e74c3c', edgecolor='#c0392b')
    ax.set_xlabel('Cosine Similarity')
    ax.set_ylabel('Count')
    ax.set_title('Similarity Distribution')
    ax.legend()
    plt.savefig(f"{save_prefix}_similarity.png", dpi=120, bbox_inches='tight')
    plt.close()

    # Plot 2: Per-Brand Accuracy
    cats = list(range(1, 11))
    accs = [per_class[c]["correct"] / per_class[c]["total"] if per_class[c]["total"] > 0 else 0 for c in cats]
    colors = ['#2ecc71' if a > 0.8 else '#f39c12' if a > 0.5 else '#e74c3c' for a in accs]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar([BRAND_NAMES[c] for c in cats], accs, color=colors, edgecolor='black')
    ax.set_ylabel('Top-1 Accuracy')
    ax.set_title('Per-Brand Retrieval Accuracy (Fine-Tuned ResNet50)')
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis='x', rotation=45)
    for bar, acc in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.02, f'{acc:.1%}', ha='center', va='bottom', fontsize=9)
    plt.savefig(f"{save_prefix}_accuracy.png", dpi=120, bbox_inches='tight')
    plt.close()


# ──────────────────────────────────────────────
# Main Pipeline
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 6K: RE-EVALUATE ON GROCERYDATASET (FINE-TUNED RESNET50)")
    print("=" * 70)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = load_finetuned_backbone()

    # 1. Build Reference Index
    print("\n" + "─" * 70)
    print("  BUILDING REFERENCE CATALOGUE INDEX")
    print("─" * 70)
    
    ref_paths, ref_labels_raw = [], []
    for cat_id in range(1, 11):
        cat_dir = CATALOGUE_DIR / str(cat_id)
        if not cat_dir.exists(): continue
        for f in sorted(cat_dir.glob('*.jpg')):
            ref_paths.append(f)
            ref_labels_raw.append({"category": cat_id, "filename": f.name})

    ref_embeddings, valid_indices = extract_embeddings_batch(model, ref_paths, desc="Catalogue references")
    ref_labels = [ref_labels_raw[i] for i in valid_indices]
    print(f"  ✅ Built reference index: {ref_embeddings.shape}")

    # 2. Primary Evaluation (GT Shelf Crops)
    print("\n" + "─" * 70)
    print("  PRIMARY EVALUATION: ProductImagesFromShelves → TRUE CATEGORY")
    print("─" * 70)
    
    gt_paths, gt_cats = [], []
    for cat_id in range(1, 11):
        cat_dir = SHELF_CROPS_DIR / str(cat_id)
        if not cat_dir.exists(): continue
        for f in sorted(cat_dir.glob('*.png')):
            gt_paths.append(f)
            gt_cats.append(cat_id)

    print(f"  Extracting embeddings for {len(gt_paths)} GT crops...")
    gt_embeddings, valid_indices = extract_embeddings_batch(model, gt_paths, desc="GT crops")
    gt_true_cats = [gt_cats[i] for i in valid_indices]
    
    retrieval = retrieve_nearest(gt_embeddings, ref_embeddings, ref_labels, top_k=TOP_K)
    
    # Compute Metrics
    top1_correct = top5_correct = 0
    per_class = defaultdict(lambda: {"correct": 0, "total": 0})
    correct_sims, incorrect_sims = [], []

    for true_cat, ret in zip(gt_true_cats, retrieval):
        pred_cat = ret["predicted_category"]
        is_correct = (pred_cat == true_cat)

        if is_correct:
            top1_correct += 1
            correct_sims.append(ret["top1_similarity"])
        else:
            incorrect_sims.append(ret["top1_similarity"])

        if true_cat in set(m["category"] for m in ret["top_matches"]):
            top5_correct += 1

        per_class[true_cat]["total"] += 1
        if is_correct: per_class[true_cat]["correct"] += 1

    total = len(gt_true_cats)
    top1_acc = top1_correct / total if total > 0 else 0
    top5_acc = top5_correct / total if total > 0 else 0

    print(f"\n  RESULTS: FINE-TUNED EMBEDDINGS (Subset)")
    print(f"    Top-1 Accuracy: {top1_acc:.4f} ({top1_correct}/{total})")
    print(f"    Top-5 Accuracy: {top5_acc:.4f} ({top5_correct}/{total})")

    print(f"\n  Per-Brand Top-1:")
    for cat_id in range(1, 11):
        d = per_class[cat_id]
        acc = d["correct"] / d["total"] if d["total"] > 0 else 0
        print(f"    {BRAND_NAMES[cat_id]:<15} {acc:>10.4f}")

    plot_metrics(correct_sims, incorrect_sims, per_class, str(OUTPUT_DIR / "finetuned"))
    print(f"\n  Saved plots to: {OUTPUT_DIR}")

    # 3. YOLO Crop Retrieval (to complete the pipeline)
    print("\n" + "─" * 70)
    print("  YOLO CROP RETRIEVAL (DIAGNOSTIC)")
    print("─" * 70)
    
    with open(YOLO_CROPS_MANIFEST) as f:
        yolo_manifest = json.load(f)
    
    yolo_paths = [YOLO_CROPS_DIR / det["crop_path"] for det in yolo_manifest]
    yolo_embeddings, valid_indices = extract_embeddings_batch(model, yolo_paths, desc="YOLO crops")
    yolo_retrieval = retrieve_nearest(yolo_embeddings, ref_embeddings, ref_labels, top_k=TOP_K)
    
    valid_manifest = [yolo_manifest[i] for i in valid_indices]
    merged = [{**det, **ret} for det, ret in zip(valid_manifest, yolo_retrieval)]
    
    with open(OUTPUT_DIR / "yolo_recognition_results.json", 'w') as f:
        json.dump(merged, f, indent=2)
    
    eval_output = {
        "model": "ResNet50 (Fine-tuned on Products-10K Prototype Subset)",
        "top1_accuracy": top1_acc,
        "top5_accuracy": top5_acc,
    }
    with open(OUTPUT_DIR / "evaluation_results.json", 'w') as f:
        json.dump(eval_output, f, indent=2)

    print("\n" + "=" * 70)
    print("  ✅ PHASE 6K COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()
