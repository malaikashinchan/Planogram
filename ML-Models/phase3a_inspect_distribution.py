"""
Phase 3A: Dataset Distribution Inspection
==========================================
Inspects the distribution of Camera IDs, Planogram IDs, Visits, Shelves,
and Category annotations across the 294 annotated shelf images.

This data will drive our train/val/test split strategy.

Usage:
    python phase3a_inspect_distribution.py
"""

import os
import re
from collections import defaultdict, Counter
from pathlib import Path


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent / "Dataset"
SHELF_IMAGES_DIR = BASE_DIR / "GroceryDataset_part1" / "ShelfImages"
PRODUCT_CROPS_DIR = BASE_DIR / "GroceryDataset_part2" / "ProductImagesFromShelves"


# ──────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────

def parse_shelf_filename(filename):
    """
    Parse shelf image filename into components.
    
    C1_P01_N1_S3_1.JPG
    │  │   │  │  └─ variant (copy number)
    │  │   │  └──── shelf number
    │  │   └─────── visit number
    │  └──────────── planogram ID
    └─────────────── camera ID
    """
    name = filename.rsplit('.', 1)[0]  # Remove extension
    parts = name.split('_')
    
    if len(parts) < 5:
        return None
    
    return {
        'camera': parts[0],        # C1, C2, C3, C4
        'planogram': parts[1],     # P01, P02, ...
        'visit': parts[2],         # N1, N2, ...
        'shelf': parts[3],         # S2, S3, ...
        'variant': parts[4],       # 1, 2, 3, ...
        'filename': filename,
    }


def parse_crop_filename(filename, category_id):
    """Parse crop filename for source image and bbox."""
    name = filename.rsplit('.png', 1)[0]
    parts = name.rsplit('_', 4)
    
    if len(parts) < 5:
        return None
    
    return {
        'source_image': parts[0],
        'category_id': category_id,
    }


def collect_annotations():
    """Collect all annotations from crop folders."""
    annotations = []
    
    for category_id in range(1, 11):
        cat_dir = PRODUCT_CROPS_DIR / str(category_id)
        if not cat_dir.exists():
            continue
        
        for fname in os.listdir(cat_dir):
            if fname.endswith('.png'):
                ann = parse_crop_filename(fname, category_id)
                if ann:
                    annotations.append(ann)
    
    return annotations


# ──────────────────────────────────────────────
# Analysis
# ──────────────────────────────────────────────

def print_section(title, char="─", width=60):
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def main():
    print("=" * 60)
    print("  PHASE 3A: DATASET DISTRIBUTION INSPECTION")
    print("=" * 60)
    
    # ── Collect annotated shelf images ──
    annotations = collect_annotations()
    
    # Group annotations by source image
    anns_by_image = defaultdict(list)
    for ann in annotations:
        anns_by_image[ann['source_image']].append(ann)
    
    annotated_images = sorted(anns_by_image.keys())
    print(f"\nTotal annotated shelf images: {len(annotated_images)}")
    print(f"Total annotations: {len(annotations)}")
    
    # Parse all annotated image filenames
    parsed_images = []
    for img_name in annotated_images:
        parsed = parse_shelf_filename(img_name)
        if parsed:
            parsed['annotations'] = anns_by_image[img_name]
            parsed['ann_count'] = len(anns_by_image[img_name])
            parsed_images.append(parsed)
    
    # ─────────────────────────────────────────
    # 1. Camera Distribution
    # ─────────────────────────────────────────
    print_section("1. CAMERA DISTRIBUTION")
    
    camera_counts = Counter(p['camera'] for p in parsed_images)
    camera_anns = defaultdict(int)
    for p in parsed_images:
        camera_anns[p['camera']] += p['ann_count']
    
    print(f"\n  {'Camera':<10} {'Images':>8} {'Annotations':>14} {'Avg Ann/Img':>14}")
    print(f"  {'──────':<10} {'──────':>8} {'───────────':>14} {'───────────':>14}")
    for cam in sorted(camera_counts.keys()):
        img_count = camera_counts[cam]
        ann_count = camera_anns[cam]
        avg = ann_count / img_count if img_count > 0 else 0
        print(f"  {cam:<10} {img_count:>8} {ann_count:>14} {avg:>14.1f}")
    
    total_imgs = sum(camera_counts.values())
    total_anns = sum(camera_anns.values())
    print(f"  {'TOTAL':<10} {total_imgs:>8} {total_anns:>14} {total_anns/total_imgs:>14.1f}")
    
    # ─────────────────────────────────────────
    # 2. Planogram Distribution
    # ─────────────────────────────────────────
    print_section("2. PLANOGRAM DISTRIBUTION")
    
    plano_counts = Counter(p['planogram'] for p in parsed_images)
    plano_anns = defaultdict(int)
    plano_categories = defaultdict(set)
    for p in parsed_images:
        plano_anns[p['planogram']] += p['ann_count']
        for ann in p['annotations']:
            plano_categories[p['planogram']].add(ann['category_id'])
    
    print(f"\n  {'Planogram':<12} {'Images':>8} {'Annotations':>14} {'Categories':>12} {'Avg Ann/Img':>14}")
    print(f"  {'─────────':<12} {'──────':>8} {'───────────':>14} {'──────────':>12} {'───────────':>14}")
    for plano in sorted(plano_counts.keys()):
        img_count = plano_counts[plano]
        ann_count = plano_anns[plano]
        cats = sorted(plano_categories[plano])
        avg = ann_count / img_count if img_count > 0 else 0
        cat_str = ",".join(str(c) for c in cats)
        print(f"  {plano:<12} {img_count:>8} {ann_count:>14} {cat_str:>12} {avg:>14.1f}")
    
    # ─────────────────────────────────────────
    # 3. Camera × Planogram Cross-Tabulation
    # ─────────────────────────────────────────
    print_section("3. CAMERA × PLANOGRAM CROSS-TABULATION (image counts)")
    
    cross = defaultdict(lambda: defaultdict(int))
    for p in parsed_images:
        cross[p['camera']][p['planogram']] += 1
    
    all_cameras = sorted(set(p['camera'] for p in parsed_images))
    all_planograms = sorted(set(p['planogram'] for p in parsed_images))
    
    # Header
    header = f"  {'':>6}"
    for plano in all_planograms:
        header += f" {plano:>5}"
    header += f" {'TOTAL':>7}"
    print(f"\n{header}")
    print(f"  {'':>6}" + "─" * (6 * len(all_planograms) + 8))
    
    for cam in all_cameras:
        row = f"  {cam:>6}"
        row_total = 0
        for plano in all_planograms:
            count = cross[cam][plano]
            row += f" {count:>5}"
            row_total += count
        row += f" {row_total:>7}"
        print(row)
    
    # Totals row
    row = f"  {'TOTAL':>6}"
    for plano in all_planograms:
        col_total = sum(cross[cam][plano] for cam in all_cameras)
        row += f" {col_total:>5}"
    row += f" {total_imgs:>7}"
    print(row)
    
    # ─────────────────────────────────────────
    # 4. Visit Distribution
    # ─────────────────────────────────────────
    print_section("4. VISIT DISTRIBUTION")
    
    visit_counts = Counter(p['visit'] for p in parsed_images)
    print(f"\n  {'Visit':<10} {'Images':>8}")
    print(f"  {'─────':<10} {'──────':>8}")
    for visit in sorted(visit_counts.keys()):
        print(f"  {visit:<10} {visit_counts[visit]:>8}")
    
    # ─────────────────────────────────────────
    # 5. Shelf Distribution
    # ─────────────────────────────────────────
    print_section("5. SHELF (ZOOM LEVEL) DISTRIBUTION")
    
    shelf_counts = Counter(p['shelf'] for p in parsed_images)
    shelf_anns = defaultdict(int)
    for p in parsed_images:
        shelf_anns[p['shelf']] += p['ann_count']
    
    print(f"\n  {'Shelf':<10} {'Images':>8} {'Annotations':>14} {'Avg Ann/Img':>14}")
    print(f"  {'─────':<10} {'──────':>8} {'───────────':>14} {'───────────':>14}")
    for shelf in sorted(shelf_counts.keys()):
        img_count = shelf_counts[shelf]
        ann_count = shelf_anns[shelf]
        avg = ann_count / img_count if img_count > 0 else 0
        print(f"  {shelf:<10} {img_count:>8} {ann_count:>14} {avg:>14.1f}")
    
    # ─────────────────────────────────────────
    # 6. Category Distribution per Planogram
    # ─────────────────────────────────────────
    print_section("6. CATEGORY DISTRIBUTION PER PLANOGRAM")
    
    cat_per_plano = defaultdict(lambda: defaultdict(int))
    for p in parsed_images:
        for ann in p['annotations']:
            cat_per_plano[p['planogram']][ann['category_id']] += 1
    
    all_cats = sorted(set(ann['category_id'] for ann in annotations))
    
    # Header
    header = f"  {'':>6}"
    for cat in all_cats:
        header += f" {'C'+str(cat):>5}"
    header += f" {'TOTAL':>7}"
    print(f"\n{header}")
    print(f"  {'':>6}" + "─" * (6 * len(all_cats) + 8))
    
    for plano in sorted(cat_per_plano.keys()):
        row = f"  {plano:>6}"
        row_total = 0
        for cat in all_cats:
            count = cat_per_plano[plano][cat]
            row += f" {count:>5}"
            row_total += count
        row += f" {row_total:>7}"
        print(row)
    
    # Totals
    row = f"  {'TOTAL':>6}"
    for cat in all_cats:
        col_total = sum(cat_per_plano[plano][cat] for plano in cat_per_plano)
        row += f" {col_total:>5}"
    row += f" {total_anns:>7}"
    print(row)
    
    # ─────────────────────────────────────────
    # 7. Planogram Group Summary (for split planning)
    # ─────────────────────────────────────────
    print_section("7. PLANOGRAM SUMMARY FOR SPLIT PLANNING")
    
    print(f"\n  Each planogram's share of total data:\n")
    print(f"  {'Planogram':<12} {'Images':>8} {'% Imgs':>8} {'Anns':>8} {'% Anns':>8} {'Categories':>12}")
    print(f"  {'─────────':<12} {'──────':>8} {'──────':>8} {'────':>8} {'──────':>8} {'──────────':>12}")
    
    for plano in sorted(plano_counts.keys()):
        img_count = plano_counts[plano]
        ann_count = plano_anns[plano]
        cats = sorted(plano_categories[plano])
        img_pct = 100 * img_count / total_imgs
        ann_pct = 100 * ann_count / total_anns
        cat_str = ",".join(str(c) for c in cats)
        print(f"  {plano:<12} {img_count:>8} {img_pct:>7.1f}% {ann_count:>8} {ann_pct:>7.1f}% {cat_str:>12}")
    
    print(f"\n  {'TOTAL':<12} {total_imgs:>8} {'100.0%':>8} {total_anns:>8} {'100.0%':>8}")
    
    print("\n" + "=" * 60)
    print("  INSPECTION COMPLETE — Use these results to plan the split")
    print("=" * 60)


if __name__ == "__main__":
    main()
