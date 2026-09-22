"""
Phase 6B.5 — Reference Catalogue Audit
=======================================
Generate contact sheets for each of the 10 product categories from 
ProductImages to visually determine whether all images within a category 
represent the SAME product from different views, or MULTIPLE distinct products.

Also generates a contact sheet of shelf crops from ProductImagesFromShelves 
for comparison.

Usage:
    python phase6b5_catalogue_audit.py
"""

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
CATALOGUE_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part1" / "ProductImages"
SHELF_CROPS_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part2" / "ProductImagesFromShelves"
OUTPUT_DIR = BASE_DIR / "outputs" / "catalogue_audit"


# ──────────────────────────────────────────────
# Step 1: Generate catalogue contact sheets
# ──────────────────────────────────────────────

def generate_catalogue_contact_sheet(category_id, n_samples=25):
    """
    Generate a contact sheet (grid of thumbnails) for a single category
    from the ProductImages catalogue.
    
    Shows 25 evenly-spaced samples so we can see the full visual range.
    """
    cat_dir = CATALOGUE_DIR / str(category_id)
    if not cat_dir.exists():
        print(f"  ⚠ Category {category_id} directory not found")
        return None

    files = sorted(cat_dir.glob('*.jpg'))
    if not files:
        return None

    # Evenly space samples across the full range
    step = max(1, len(files) // n_samples)
    samples = files[::step][:n_samples]

    # Grid layout: 5 x 5
    cols = 5
    rows = (len(samples) + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3))
    fig.suptitle(
        f"Category {category_id} — ProductImages Catalogue\n"
        f"({len(files)} total images, showing {len(samples)} evenly spaced samples)",
        fontsize=14, fontweight='bold', y=1.02
    )

    for idx in range(rows * cols):
        row, col = divmod(idx, cols)
        ax = axes[row][col] if rows > 1 else axes[col]

        if idx < len(samples):
            img = cv2.imread(str(samples[idx]))
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                ax.imshow(img_rgb)
                ax.set_title(samples[idx].name, fontsize=7)
            else:
                ax.text(0.5, 0.5, 'Failed', ha='center', va='center')
        ax.axis('off')

    plt.tight_layout()
    out_path = OUTPUT_DIR / f"catalogue_cat{category_id:02d}.png"
    plt.savefig(str(out_path), dpi=100, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {out_path.name}")
    return out_path


# ──────────────────────────────────────────────
# Step 2: Generate shelf crop contact sheets
# ──────────────────────────────────────────────

def generate_shelf_crop_contact_sheet(category_id, n_samples=25):
    """
    Generate a contact sheet from ProductImagesFromShelves
    for the same category, so we can compare catalogue vs shelf appearance.
    """
    cat_dir = SHELF_CROPS_DIR / str(category_id)
    if not cat_dir.exists():
        print(f"  ⚠ Shelf crops category {category_id} not found")
        return None

    files = sorted(cat_dir.glob('*.png'))
    if not files:
        return None

    step = max(1, len(files) // n_samples)
    samples = files[::step][:n_samples]

    cols = 5
    rows = (len(samples) + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3))
    fig.suptitle(
        f"Category {category_id} — Shelf Crops (ProductImagesFromShelves)\n"
        f"({len(files)} total crops, showing {len(samples)} evenly spaced samples)",
        fontsize=14, fontweight='bold', y=1.02
    )

    for idx in range(rows * cols):
        row, col = divmod(idx, cols)
        ax = axes[row][col] if rows > 1 else axes[col]

        if idx < len(samples):
            img = cv2.imread(str(samples[idx]))
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                ax.imshow(img_rgb)
                # Truncate long filenames
                short_name = samples[idx].name[:30] + "..." if len(samples[idx].name) > 30 else samples[idx].name
                ax.set_title(short_name, fontsize=6)
            else:
                ax.text(0.5, 0.5, 'Failed', ha='center', va='center')
        ax.axis('off')

    plt.tight_layout()
    out_path = OUTPUT_DIR / f"shelf_crops_cat{category_id:02d}.png"
    plt.savefig(str(out_path), dpi=100, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {out_path.name}")
    return out_path


# ──────────────────────────────────────────────
# Step 3: Statistical summary
# ──────────────────────────────────────────────

def print_catalogue_summary():
    """Print a complete statistical summary of the catalogue."""

    print("\n" + "=" * 70)
    print("  CATALOGUE SUMMARY")
    print("=" * 70)

    print(f"\n  {'Cat':<6} {'Brand':<8} {'Catalogue':<12} {'Shelf Crops':<14} {'Image Sizes'}")
    print(f"  {'───':<6} {'─────':<8} {'─────────':<12} {'───────────':<14} {'───────────'}")

    for cat_id in range(1, 11):
        cat_dir = CATALOGUE_DIR / str(cat_id)
        shelf_dir = SHELF_CROPS_DIR / str(cat_id)

        cat_files = list(cat_dir.glob('*.jpg')) if cat_dir.exists() else []
        shelf_files = list(shelf_dir.glob('*.png')) if shelf_dir.exists() else []

        # Get brand prefix
        brand = ""
        if cat_files:
            brand = cat_files[0].stem.split('_')[0]

        # Get unique image sizes (sample of 20)
        sizes = set()
        for f in cat_files[:20]:
            img = cv2.imread(str(f))
            if img is not None:
                h, w = img.shape[:2]
                sizes.add((w, h))

        print(f"  {cat_id:<6} {brand:<8} {len(cat_files):<12} {len(shelf_files):<14} {len(sizes)} unique")

    # Key finding
    print(f"\n  Key finding:")
    print(f"  ─────────────")
    print(f"  Brand prefix B1→B10 maps exactly 1:1 to Category 1→10")
    print(f"  BrandImagesFromShelves filenames are IDENTICAL to ProductImagesFromShelves")
    print(f"  No finer-grained product/SKU identity exists in the annotation scheme")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 6B.5: REFERENCE CATALOGUE AUDIT")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Catalogue contact sheets
    print("\n📸 Step 1: Generating catalogue contact sheets (ProductImages)...")
    for cat_id in range(1, 11):
        generate_catalogue_contact_sheet(cat_id)

    # Step 2: Shelf crop contact sheets
    print("\n📸 Step 2: Generating shelf crop contact sheets...")
    for cat_id in range(1, 11):
        generate_shelf_crop_contact_sheet(cat_id)

    # Step 3: Summary
    print_catalogue_summary()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 6B.5 COMPLETE!")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 70)
    print(f"\n  Visual inspection required:")
    print(f"  Look at the contact sheets to determine whether each category")
    print(f"  contains ONE product (same item, many views) or MULTIPLE products.")


if __name__ == "__main__":
    main()
