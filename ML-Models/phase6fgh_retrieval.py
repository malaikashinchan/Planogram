"""
Phase 6F+6G+6H — Similarity Retrieval, Confidence Analysis & Evaluation
=========================================================================
6F: For each crop, find Top-K nearest reference images via cosine similarity.
6G: Analyze similarity/margin distributions (no hardcoded threshold).
6H-A: YOLO crop → YOLO category agreement (diagnostic only).
6H-B: ProductImagesFromShelves → true category (primary evaluation).

Usage:
    python phase6fgh_retrieval.py
"""

import cv2
import json
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
EMBEDDINGS_DIR = BASE_DIR / "outputs" / "embeddings"
SHELF_CROPS_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part2" / "ProductImagesFromShelves"
CATALOGUE_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part1" / "ProductImages"
OUTPUT_DIR = BASE_DIR / "outputs" / "retrieval"

TOP_K = 5

# Project-defined brand identities (not retailer SKUs)
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
# 6F: Similarity Retrieval
# ──────────────────────────────────────────────

def retrieve_nearest(query_embeddings, ref_embeddings, ref_labels, top_k=5):
    """
    For each query embedding, find top-K nearest reference images.
    
    SKU aggregation: per-SKU score = max reference similarity for that SKU.
    
    Returns list of retrieval result dicts.
    """
    print(f"\n  Computing similarity: {query_embeddings.shape[0]} queries × "
          f"{ref_embeddings.shape[0]} references...")

    # L2-normalized → dot product = cosine similarity
    sim_matrix = query_embeddings @ ref_embeddings.T

    results = []
    for i in range(sim_matrix.shape[0]):
        sims = sim_matrix[i]
        top_indices = np.argsort(sims)[::-1][:top_k]

        # Image-level top-K matches
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

        # Aggregate by brand: max similarity per brand
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
        margin = top1_sim - top2_sim

        results.append({
            "predicted_category": top1_cat,
            "predicted_brand": BRAND_NAMES.get(top1_cat, "Unknown"),
            "top1_similarity": float(top1_sim),
            "top2_category": top2_cat,
            "top2_brand": BRAND_NAMES.get(top2_cat, "Unknown") if top2_cat else None,
            "top2_similarity": float(top2_sim),
            "margin": float(margin),
            "top_matches": top_matches,
        })

    print(f"  ✅ Retrieval complete for {len(results)} queries")
    return results


# ──────────────────────────────────────────────
# 6G: Confidence / Distribution Analysis
# ──────────────────────────────────────────────

def analyze_distributions(retrieval_results, label=""):
    """Analyze and plot similarity and margin distributions."""

    sims = [r["top1_similarity"] for r in retrieval_results]
    margins = [r["margin"] for r in retrieval_results]

    print(f"\n  {label} — Distribution Analysis:")
    print(f"    Top-1 Similarity: mean={np.mean(sims):.4f}, "
          f"min={np.min(sims):.4f}, max={np.max(sims):.4f}")
    print(f"    Margin (top1−top2): mean={np.mean(margins):.4f}, "
          f"min={np.min(margins):.4f}, max={np.max(margins):.4f}")

    return sims, margins


def plot_similarity_distribution(correct_sims, incorrect_sims, save_path):
    """Plot correct vs incorrect similarity distributions."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(correct_sims, bins=40, alpha=0.7, label=f'Correct ({len(correct_sims)})',
            color='#2ecc71', edgecolor='#27ae60')
    if incorrect_sims:
        ax.hist(incorrect_sims, bins=40, alpha=0.7, label=f'Incorrect ({len(incorrect_sims)})',
                color='#e74c3c', edgecolor='#c0392b')
    ax.set_xlabel('Cosine Similarity (Top-1)')
    ax.set_ylabel('Count')
    ax.set_title('Similarity Distribution: Correct vs Incorrect Brand Retrieval')
    ax.legend()
    plt.tight_layout()
    plt.savefig(str(save_path), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {save_path.name}")


def plot_margin_distribution(correct_margins, incorrect_margins, save_path):
    """Plot correct vs incorrect margin distributions."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(correct_margins, bins=40, alpha=0.7, label=f'Correct ({len(correct_margins)})',
            color='#2ecc71', edgecolor='#27ae60')
    if incorrect_margins:
        ax.hist(incorrect_margins, bins=40, alpha=0.7, label=f'Incorrect ({len(incorrect_margins)})',
                color='#e74c3c', edgecolor='#c0392b')
    ax.set_xlabel('Margin (Top-1 similarity − Top-2 similarity)')
    ax.set_ylabel('Count')
    ax.set_title('Margin Distribution: Correct vs Incorrect Brand Retrieval')
    ax.legend()
    plt.tight_layout()
    plt.savefig(str(save_path), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {save_path.name}")


def plot_confusion_matrix(true_cats, pred_cats, save_path):
    """Plot confusion matrix for brand retrieval."""
    n_classes = 10
    matrix = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(true_cats, pred_cats):
        matrix[t - 1][p - 1] += 1

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix, cmap='Blues')

    labels = [BRAND_NAMES[i] for i in range(1, 11)]
    ax.set_xticks(range(n_classes))
    ax.set_yticks(range(n_classes))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Predicted Brand')
    ax.set_ylabel('True Brand')
    ax.set_title('Brand Retrieval Confusion Matrix (ProductImagesFromShelves)')

    # Add text annotations
    for i in range(n_classes):
        for j in range(n_classes):
            val = matrix[i][j]
            if val > 0:
                color = 'white' if val > matrix.max() * 0.5 else 'black'
                ax.text(j, i, str(val), ha='center', va='center',
                        fontsize=7, color=color)

    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig(str(save_path), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {save_path.name}")


def plot_per_brand_accuracy(per_class_data, save_path):
    """Plot per-brand accuracy bar chart."""
    cats = list(range(1, 11))
    accs = []
    for c in cats:
        d = per_class_data[c]
        accs.append(d["correct"] / d["total"] if d["total"] > 0 else 0)

    colors = ['#2ecc71' if a > 0.8 else '#f39c12' if a > 0.5 else '#e74c3c' for a in accs]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar([BRAND_NAMES[c] for c in cats], accs, color=colors, edgecolor='black')
    ax.set_ylabel('Top-1 Accuracy')
    ax.set_title('Per-Brand Retrieval Accuracy (ResNet50 Frozen Baseline)')
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis='x', rotation=45)

    for bar, acc in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.02,
                f'{acc:.1%}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(str(save_path), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {save_path.name}")


# ──────────────────────────────────────────────
# 6H-A: YOLO Crop → YOLO Category Agreement
# ──────────────────────────────────────────────

def evaluate_yolo_agreement(retrieval_results, crop_manifest):
    """
    Diagnostic: does retrieval agree with YOLO's predicted category?
    This is NOT ground-truth accuracy — only measures internal consistency.
    """
    print("\n" + "─" * 70)
    print("  6H-A: YOLO CROP → YOLO CATEGORY AGREEMENT (DIAGNOSTIC ONLY)")
    print("─" * 70)

    agree = 0
    total = len(retrieval_results)

    for ret, det in zip(retrieval_results, crop_manifest):
        yolo_cat = det["yolo_class"] + 1  # 0-indexed → 1-indexed
        retrieved_cat = ret["predicted_category"]
        if yolo_cat == retrieved_cat:
            agree += 1

    agreement_rate = agree / total if total > 0 else 0

    print(f"\n  Agreement rate: {agreement_rate:.4f} ({agree}/{total})")
    print(f"  (This measures whether retrieval agrees with YOLO prediction,")
    print(f"   NOT whether either is correct against ground truth.)")

    return {"agreement_rate": agreement_rate, "agree": agree, "total": total}


# ──────────────────────────────────────────────
# 6H-B: ProductImagesFromShelves Evaluation
# ──────────────────────────────────────────────

def build_feature_extractor():
    """Load frozen ResNet50 for embedding extraction."""
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    model = nn.Sequential(*list(model.children())[:-1])
    model.eval()
    model.to(DEVICE)
    return model


def extract_embeddings_batch(model, image_paths, batch_size=64, desc=""):
    """Extract L2-normalized embeddings for a list of image paths."""
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
                tensor = TRANSFORM(img_rgb)
                tensors.append(tensor)
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


def evaluate_gt_crops(model, ref_embeddings, ref_labels):
    """
    Primary evaluation using ProductImagesFromShelves.
    True labels come from directory structure (dataset annotations).
    """
    print("\n" + "─" * 70)
    print("  6H-B: ProductImagesFromShelves → TRUE CATEGORY (PRIMARY EVALUATION)")
    print("─" * 70)

    # Collect ground-truth crops (skip category 0 = background)
    gt_paths = []
    gt_categories = []

    for cat_id in range(1, 11):
        cat_dir = SHELF_CROPS_DIR / str(cat_id)
        if not cat_dir.exists():
            continue
        files = sorted(cat_dir.glob('*.png'))
        for f in files:
            gt_paths.append(f)
            gt_categories.append(cat_id)

    print(f"  Ground-truth shelf crops: {len(gt_paths)} (categories 1–10)")

    # Leakage check: ensure no filenames overlap with ProductImages catalogue
    ref_filenames = set()
    for cat_id in range(1, 11):
        cat_dir = CATALOGUE_DIR / str(cat_id)
        if cat_dir.exists():
            for f in cat_dir.glob('*.jpg'):
                ref_filenames.add(f.name)

    gt_filenames = set(f.name for f in gt_paths)
    overlap = ref_filenames & gt_filenames
    if overlap:
        print(f"  ⚠ WARNING: {len(overlap)} filenames overlap between reference and eval sets!")
    else:
        print(f"  ✅ No filename overlap was found between the reference (ProductImages) and "
              f"eval (ProductImagesFromShelves) sets.")

    # Extract embeddings
    print(f"\n  Extracting embeddings for GT crops...")
    gt_embeddings, valid_indices = extract_embeddings_batch(
        model, gt_paths, desc="GT crops"
    )
    gt_true_cats = [gt_categories[i] for i in valid_indices]
    print(f"  ✅ {len(gt_true_cats)} GT crop embeddings extracted")

    # Retrieve
    retrieval = retrieve_nearest(gt_embeddings, ref_embeddings, ref_labels, top_k=TOP_K)

    # Compute metrics
    top1_correct = 0
    top5_correct = 0
    per_class = defaultdict(lambda: {"correct": 0, "total": 0})
    correct_sims = []
    incorrect_sims = []
    correct_margins = []
    incorrect_margins = []
    true_cats_list = []
    pred_cats_list = []

    for true_cat, ret in zip(gt_true_cats, retrieval):
        pred_cat = ret["predicted_category"]
        is_correct = (pred_cat == true_cat)

        true_cats_list.append(true_cat)
        pred_cats_list.append(pred_cat)

        # Top-1
        if is_correct:
            top1_correct += 1
            correct_sims.append(ret["top1_similarity"])
            correct_margins.append(ret["margin"])
        else:
            incorrect_sims.append(ret["top1_similarity"])
            incorrect_margins.append(ret["margin"])

        # Top-5: check if true category appears in any top-5 match
        top5_cats = set(m["category"] for m in ret["top_matches"])
        if true_cat in top5_cats:
            top5_correct += 1

        per_class[true_cat]["total"] += 1
        if is_correct:
            per_class[true_cat]["correct"] += 1

    total = len(gt_true_cats)
    top1_acc = top1_correct / total if total > 0 else 0
    top5_acc = top5_correct / total if total > 0 else 0

    # ── Print results ──
    print(f"\n" + "=" * 70)
    print(f"  BRAND/CATEGORY RETRIEVAL — PRIMARY RESULTS")
    print(f"  (ResNet50 frozen, no category filtering, ProductImagesFromShelves GT)")
    print(f"=" * 70)

    print(f"\n  Overall:")
    print(f"    Top-1 Accuracy: {top1_acc:.4f} ({top1_correct}/{total})")
    print(f"    Top-5 Accuracy: {top5_acc:.4f} ({top5_correct}/{total})")

    print(f"\n  Per-Brand Top-1 Accuracy:")
    print(f"    {'Brand':<15} {'Accuracy':>10} {'Correct/Total':>15}")
    print(f"    {'─────':<15} {'────────':>10} {'─────────────':>15}")
    for cat_id in range(1, 11):
        d = per_class[cat_id]
        acc = d["correct"] / d["total"] if d["total"] > 0 else 0
        print(f"    {BRAND_NAMES[cat_id]:<15} {acc:>10.4f} {d['correct']:>6}/{d['total']:<6}")

    print(f"\n  Similarity Distribution:")
    print(f"    Correct:   mean={np.mean(correct_sims):.4f} "
          f"[{np.min(correct_sims):.4f}, {np.max(correct_sims):.4f}]")
    if incorrect_sims:
        print(f"    Incorrect: mean={np.mean(incorrect_sims):.4f} "
              f"[{np.min(incorrect_sims):.4f}, {np.max(incorrect_sims):.4f}]")

    print(f"\n  Margin Distribution:")
    print(f"    Correct:   mean={np.mean(correct_margins):.4f}")
    if incorrect_margins:
        print(f"    Incorrect: mean={np.mean(incorrect_margins):.4f}")

    # ── Plots ──
    print(f"\n  Generating plots...")

    plot_similarity_distribution(
        correct_sims, incorrect_sims,
        OUTPUT_DIR / "similarity_distribution.png"
    )
    plot_margin_distribution(
        correct_margins, incorrect_margins,
        OUTPUT_DIR / "margin_distribution.png"
    )
    plot_confusion_matrix(
        true_cats_list, pred_cats_list,
        OUTPUT_DIR / "confusion_matrix.png"
    )
    plot_per_brand_accuracy(per_class, OUTPUT_DIR / "per_brand_accuracy.png")

    return {
        "top1_accuracy": top1_acc,
        "top5_accuracy": top5_acc,
        "total_eval_crops": total,
        "correct_sim_mean": float(np.mean(correct_sims)),
        "correct_sim_range": [float(np.min(correct_sims)), float(np.max(correct_sims))],
        "incorrect_sim_mean": float(np.mean(incorrect_sims)) if incorrect_sims else None,
        "incorrect_sim_range": [float(np.min(incorrect_sims)), float(np.max(incorrect_sims))] if incorrect_sims else None,
        "correct_margin_mean": float(np.mean(correct_margins)),
        "incorrect_margin_mean": float(np.mean(incorrect_margins)) if incorrect_margins else None,
        "per_class": {
            BRAND_NAMES[c]: {
                "accuracy": per_class[c]["correct"] / per_class[c]["total"] if per_class[c]["total"] > 0 else 0,
                "correct": per_class[c]["correct"],
                "total": per_class[c]["total"],
            }
            for c in range(1, 11)
        },
    }


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 6F+6G+6H: RETRIEVAL, CONFIDENCE & EVALUATION")
    print("=" * 70)

    import shutil
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load pre-computed embeddings
    print("\n📦 Loading embeddings...")
    ref_embeddings = np.load(str(EMBEDDINGS_DIR / "reference_embeddings.npy"))
    crop_embeddings = np.load(str(EMBEDDINGS_DIR / "crop_embeddings.npy"))

    with open(EMBEDDINGS_DIR / "reference_labels.json") as f:
        ref_labels = json.load(f)
    with open(EMBEDDINGS_DIR / "crop_manifest.json") as f:
        crop_manifest = json.load(f)

    print(f"  Reference index: {ref_embeddings.shape}")
    print(f"  YOLO crops:      {crop_embeddings.shape}")

    start_time = time.time()

    # ── PHASE 6F ──
    print("\n" + "─" * 70)
    print("  PHASE 6F: SIMILARITY RETRIEVAL ON YOLO CROPS")
    print("─" * 70)

    crop_retrieval = retrieve_nearest(
        crop_embeddings, ref_embeddings, ref_labels, top_k=TOP_K
    )

    # Merge retrieval with manifest
    merged = []
    for ret, det in zip(crop_retrieval, crop_manifest):
        merged.append({**det, **ret})

    with open(OUTPUT_DIR / "retrieval_results.json", 'w') as f:
        json.dump(merged, f, indent=2)
    print(f"  Saved: retrieval_results.json ({len(merged)} entries)")

    # ── PHASE 6G ──
    print("\n" + "─" * 70)
    print("  PHASE 6G: CONFIDENCE / DISTRIBUTION ANALYSIS")
    print("─" * 70)

    analyze_distributions(crop_retrieval, label="YOLO Crops")

    # ── PHASE 6H-A ──
    yolo_agreement = evaluate_yolo_agreement(crop_retrieval, crop_manifest)

    # ── PHASE 6H-B ──
    model = build_feature_extractor()
    gt_eval = evaluate_gt_crops(model, ref_embeddings, ref_labels)

    elapsed = time.time() - start_time

    # ── Save evaluation metrics ──
    eval_output = {
        "model": "ResNet50 (ImageNet V2 pretrained, frozen)",
        "embedding_dim": 2048,
        "num_references": int(ref_embeddings.shape[0]),
        "num_yolo_crops": int(crop_embeddings.shape[0]),
        "evaluation_a_yolo_agreement": yolo_agreement,
        "evaluation_b_gt_accuracy": gt_eval,
        "elapsed_seconds": round(elapsed, 1),
    }

    with open(OUTPUT_DIR / "evaluation_results.json", 'w') as f:
        json.dump(eval_output, f, indent=2)
    print(f"\n  Saved: evaluation_results.json")

    # Final summary
    print("\n" + "=" * 70)
    print("  ✅ PHASE 6F+6G+6H COMPLETE!")
    print("=" * 70)
    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"\n  Output files:")
    print(f"    retrieval_results.json     — Full retrieval for all YOLO crops")
    print(f"    evaluation_results.json    — All evaluation metrics")
    print(f"    similarity_distribution.png")
    print(f"    margin_distribution.png")
    print(f"    confusion_matrix.png")
    print(f"    per_brand_accuracy.png")


if __name__ == "__main__":
    main()
