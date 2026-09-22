"""
Phase 3B: Convert to YOLO Format
=================================
Converts the Freiburg Grocery Dataset annotations (bounding box coordinates
embedded in crop filenames) into YOLO format with a planogram-based
train/val/test split.

Conversion:
    Category 1-10  →  YOLO class 0-9
    (x, y, w, h)   →  (cx, cy, w, h) normalized to [0, 1]

Split (by planogram, no data leakage):
    Train: P01, P02, P03, P05, P09, P10, P11, P12  (166 images, 56.5%)
    Val:   P04, P06                                  (63 images, 21.4%)
    Test:  P07, P08                                  (65 images, 22.1%)

Output:
    dataset_yolo/
    ├── images/{train,val,test}/    (copies of shelf images)
    ├── labels/{train,val,test}/    (YOLO .txt label files)
    └── data.yaml

Usage:
    python convert_to_yolo.py
"""

import os
import shutil
from collections import defaultdict, Counter
from pathlib import Path
from PIL import Image


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "Dataset"
SHELF_IMAGES_DIR = DATASET_DIR / "GroceryDataset_part1" / "ShelfImages"
PRODUCT_CROPS_DIR = DATASET_DIR / "GroceryDataset_part2" / "ProductImagesFromShelves"
OUTPUT_DIR = BASE_DIR / "dataset_yolo"

# Planogram-based split (no data leakage)
SPLIT_CONFIG = {
    'train': ['P01', 'P02', 'P03', 'P05', 'P09', 'P10', 'P11', 'P12'],
    'val':   ['P04', 'P06'],
    'test':  ['P07', 'P08'],
}

# Category 1-10 → YOLO class 0-9
NUM_CLASSES = 10
CLASS_NAMES = {
    0: 'Cat-1',  1: 'Cat-2',  2: 'Cat-3',  3: 'Cat-4',  4: 'Cat-5',
    5: 'Cat-6',  6: 'Cat-7',  7: 'Cat-8',  8: 'Cat-9',  9: 'Cat-10',
}


# ──────────────────────────────────────────────
# Step 1: Parse crop filenames → annotations
# ──────────────────────────────────────────────

def parse_crop_filename(filename, category_id):
    """
    Parse a crop filename to extract source shelf image and bounding box.

    Example:
        C1_P01_N1_S3_1.JPG_1276_1828_276_448.png
        → source: C1_P01_N1_S3_1.JPG
        → bbox:   x=1276, y=1828, w=276, h=448
        → YOLO class: category_id - 1  (so Cat-1 → class 0)
    """
    name = filename.rsplit('.png', 1)[0]
    parts = name.rsplit('_', 4)

    if len(parts) < 5:
        return None

    try:
        x = int(parts[1])
        y = int(parts[2])
        w = int(parts[3])
        h = int(parts[4])
    except ValueError:
        return None

    return {
        'source_image': parts[0],
        'bbox_xywh': (x, y, w, h),
        'category_id': category_id,        # original 1-10
        'yolo_class': category_id - 1,      # YOLO 0-9
    }


def parse_shelf_filename(filename):
    """Extract planogram ID from shelf image filename."""
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_')
    if len(parts) >= 2:
        return parts[1]  # e.g., 'P01'
    return None


def collect_all_annotations():
    """Walk category folders 1-10 and parse every crop filename."""
    annotations = []

    for category_id in range(1, 11):
        cat_dir = PRODUCT_CROPS_DIR / str(category_id)
        if not cat_dir.exists():
            print(f"  ⚠ Category {category_id} folder not found, skipping")
            continue

        for fname in os.listdir(cat_dir):
            if fname.endswith('.png'):
                ann = parse_crop_filename(fname, category_id)
                if ann:
                    annotations.append(ann)

    return annotations


# ──────────────────────────────────────────────
# Step 2: Convert pixel coords → YOLO normalized
# ──────────────────────────────────────────────

def pixel_to_yolo(x, y, w, h, img_width, img_height):
    """
    Convert pixel (x, y, w, h) to YOLO normalized (cx, cy, w, h).

    x, y = top-left corner of bounding box (pixels)
    w, h = width, height of bounding box (pixels)

    Returns:
        (cx, cy, norm_w, norm_h) all in [0, 1]
    """
    cx = (x + w / 2.0) / img_width
    cy = (y + h / 2.0) / img_height
    norm_w = w / img_width
    norm_h = h / img_height

    return cx, cy, norm_w, norm_h


def validate_yolo_coords(cx, cy, w, h, source_image, bbox_orig):
    """
    Validate YOLO coordinates.

    Tiny floating-point boundary errors are allowed.
    Real out-of-bounds annotations are reported and skipped.
    """
    issues = []
    is_valid = True

    # Very small floating-point tolerance
    eps = 1e-6

    # Check width and height
    if w <= 0 or h <= 0:
        issues.append(
            f"  ❌ INVALID BOX SIZE: w={w:.6f}, h={h:.6f} "
            f"in {source_image} (bbox: {bbox_orig})"
        )
        is_valid = False

    # Check individual YOLO values
    for name, val in [('cx', cx), ('cy', cy), ('w', w), ('h', h)]:
        if val < -eps or val > 1 + eps:
            issues.append(
                f"  ❌ MAJOR OUT OF BOUNDS: {name}={val:.6f} "
                f"in {source_image} (bbox: {bbox_orig})"
            )
            is_valid = False
        elif val < 0 or val > 1:
            issues.append(
                f"  ⚠ Minor floating-point boundary issue: "
                f"{name}={val:.9f} in {source_image}"
            )

    # Check whether the actual box extends outside the image
    min_x = cx - w / 2
    max_x = cx + w / 2
    min_y = cy - h / 2
    max_y = cy + h / 2

    if min_x < -eps or max_x > 1 + eps:
        issues.append(
            f"  ❌ BOX EXTENDS BEYOND IMAGE (X): {source_image} "
            f"(min_x={min_x:.6f}, max_x={max_x:.6f})"
        )
        is_valid = False
    elif min_x < 0 or max_x > 1:
        issues.append(
            f"  ⚠ Minor floating-point box boundary issue (X): "
            f"{source_image}"
        )

    if min_y < -eps or max_y > 1 + eps:
        issues.append(
            f"  ❌ BOX EXTENDS BEYOND IMAGE (Y): {source_image} "
            f"(min_y={min_y:.6f}, max_y={max_y:.6f})"
        )
        is_valid = False
    elif min_y < 0 or max_y > 1:
        issues.append(
            f"  ⚠ Minor floating-point box boundary issue (Y): "
            f"{source_image}"
        )

    return is_valid, issues


# ──────────────────────────────────────────────
# Step 3: Assign splits & build YOLO dataset
# ──────────────────────────────────────────────

def get_split_for_planogram(planogram_id):
    """Return 'train', 'val', or 'test' based on planogram ID."""
    for split_name, planograms in SPLIT_CONFIG.items():
        if planogram_id in planograms:
            return split_name
    return None  # Unknown planogram


def build_yolo_dataset(annotations):
    """
    Main conversion pipeline:
    1. Group annotations by source shelf image
    2. Get image dimensions
    3. Convert to YOLO format
    4. Assign to train/val/test split
    5. Copy images and write label files
    """

    # Group annotations by source image
    anns_by_image = defaultdict(list)
    for ann in annotations:
        anns_by_image[ann['source_image']].append(ann)

    print(f"  {len(anns_by_image)} shelf images with annotations")

    # Clean old output directory if it exists to avoid stale files
    if OUTPUT_DIR.exists():
        print(f"  🧹 Cleaning old output directory: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    # Create output directories
    for split in ['train', 'val', 'test']:
        (OUTPUT_DIR / 'images' / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / 'labels' / split).mkdir(parents=True, exist_ok=True)

    # Tracking
    split_counts = Counter()        # images per split
    split_ann_counts = Counter()    # annotations per split
    split_cat_counts = defaultdict(lambda: Counter())  # category per split
    all_issues = []
    skipped_images = []
    image_dimensions = {}           # cache

    total = len(anns_by_image)

    for i, (shelf_name, anns) in enumerate(sorted(anns_by_image.items()), 1):

        # Determine planogram → split
        planogram_id = parse_shelf_filename(shelf_name)
        if planogram_id is None:
            skipped_images.append((shelf_name, "Could not parse planogram ID"))
            continue

        split = get_split_for_planogram(planogram_id)
        if split is None:
            skipped_images.append((shelf_name, f"Unknown planogram {planogram_id}"))
            continue

        # Check source image exists
        src_path = SHELF_IMAGES_DIR / shelf_name
        if not src_path.exists():
            skipped_images.append((shelf_name, "Shelf image not found"))
            continue

        # Get image dimensions (using PIL, reads only header)
        if shelf_name not in image_dimensions:
            with Image.open(src_path) as img:
                image_dimensions[shelf_name] = img.size  # (width, height)

        img_width, img_height = image_dimensions[shelf_name]

        # Convert all annotations for this image
        yolo_lines = []
        for ann in anns:
            x, y, w, h = ann['bbox_xywh']
            cx, cy, nw, nh = pixel_to_yolo(x, y, w, h, img_width, img_height)

            # Validate
            is_valid, issues = validate_yolo_coords(cx, cy, nw, nh, shelf_name, (x, y, w, h))
            all_issues.extend(issues)
            
            if not is_valid:
                # Skip major annotation errors
                continue

            # Correct ONLY tiny floating-point boundary errors
            eps = 1e-6

            if -eps <= cx < 0:
                cx = 0.0
            elif 1 < cx <= 1 + eps:
                cx = 1.0

            if -eps <= cy < 0:
                cy = 0.0
            elif 1 < cy <= 1 + eps:
                cy = 1.0

            if -eps <= nw < 0:
                nw = 0.0
            elif 1 < nw <= 1 + eps:
                nw = 1.0

            if -eps <= nh < 0:
                nh = 0.0
            elif 1 < nh <= 1 + eps:
                nh = 1.0

            yolo_lines.append(f"{ann['yolo_class']} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

            # Track
            split_cat_counts[split][ann['yolo_class']] += 1

        # If every annotation was invalid, skip the entire image
        if not yolo_lines:
            skipped_images.append(
                (shelf_name, "No valid annotations remained")
            )
            continue

        # Copy image to split directory
        dst_img_path = OUTPUT_DIR / 'images' / split / shelf_name
        if not dst_img_path.exists():
            shutil.copy2(str(src_path), str(dst_img_path))

        # Write YOLO label file
        label_name = shelf_name.rsplit('.', 1)[0] + '.txt'
        label_path = OUTPUT_DIR / 'labels' / split / label_name
        with open(label_path, 'w') as f:
            f.write('\n'.join(yolo_lines) + '\n')

        split_counts[split] += 1
        split_ann_counts[split] += len(yolo_lines)

        if i % 50 == 0 or i == total:
            print(f"  Processed {i}/{total} images...")

    return split_counts, split_ann_counts, split_cat_counts, all_issues, skipped_images


# ──────────────────────────────────────────────
# Step 4: Generate data.yaml
# ──────────────────────────────────────────────

def write_data_yaml():
    """Write YOLO data.yaml configuration file."""
    yaml_content = f"""# Planogram Grocery Dataset - YOLO Format
# Generated by Phase 3B: convert_to_yolo.py
#
# Split strategy: By planogram ID (no data leakage)
#   Train: P01, P02, P03, P05, P09, P10, P11, P12
#   Val:   P04, P06
#   Test:  P07, P08

path: {OUTPUT_DIR.resolve()}

train: images/train
val: images/val
test: images/test

nc: {NUM_CLASSES}

names:
"""
    for class_id in range(NUM_CLASSES):
        yaml_content += f"  {class_id}: {CLASS_NAMES[class_id]}\n"

    yaml_path = OUTPUT_DIR / 'data.yaml'
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f"  Saved: {yaml_path}")


# ──────────────────────────────────────────────
# Step 5: Print summary
# ──────────────────────────────────────────────

def print_summary(split_counts, split_ann_counts, split_cat_counts, issues, skipped):
    """Print comprehensive conversion summary."""

    print("\n" + "=" * 70)
    print("  CONVERSION SUMMARY")
    print("=" * 70)

    # Split overview
    total_imgs = sum(split_counts.values())
    total_anns = sum(split_ann_counts.values())

    print(f"\n  {'Split':<8} {'Images':>8} {'%':>7} {'Annotations':>14} {'%':>7} {'Planograms'}")
    print(f"  {'─────':<8} {'──────':>8} {'─':>7} {'───────────':>14} {'─':>7} {'──────────'}")
    for split in ['train', 'val', 'test']:
        imgs = split_counts[split]
        anns = split_ann_counts[split]
        img_pct = 100 * imgs / total_imgs if total_imgs > 0 else 0
        ann_pct = 100 * anns / total_anns if total_anns > 0 else 0
        planos = ', '.join(SPLIT_CONFIG[split])
        print(f"  {split:<8} {imgs:>8} {img_pct:>6.1f}% {anns:>14} {ann_pct:>6.1f}%  {planos}")
    print(f"  {'TOTAL':<8} {total_imgs:>8} {'100.0%':>7} {total_anns:>14} {'100.0%':>7}")

    # Per-split category distribution table
    print(f"\n  {'':>12}", end='')
    for split in ['train', 'val', 'test']:
        print(f" {split:>8}", end='')
    print(f" {'TOTAL':>8}")

    print(f"  {'':>12}", end='')
    for _ in ['train', 'val', 'test', 'TOTAL']:
        print(f" {'────────':>8}", end='')
    print()

    for class_id in range(NUM_CLASSES):
        label = CLASS_NAMES[class_id]
        print(f"  {label:>12}", end='')
        row_total = 0
        for split in ['train', 'val', 'test']:
            count = split_cat_counts[split][class_id]
            row_total += count
            print(f" {count:>8}", end='')
        print(f" {row_total:>8}")

    # Totals row
    print(f"  {'TOTAL':>12}", end='')
    for split in ['train', 'val', 'test']:
        col_total = sum(split_cat_counts[split].values())
        print(f" {col_total:>8}", end='')
    print(f" {total_anns:>8}")

    # Validation issues
    if issues:
        print(f"\n  ⚠ VALIDATION ISSUES ({len(issues)}):")
        for issue in issues[:20]:  # Show first 20
            print(f"  {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print(f"\n  ✅ No validation issues — all coordinates within [0, 1]")

    # Skipped images
    if skipped:
        print(f"\n  ⚠ SKIPPED IMAGES ({len(skipped)}):")
        for name, reason in skipped:
            print(f"    {name} — {reason}")
    else:
        print(f"  ✅ No images skipped")


# ──────────────────────────────────────────────
# Step 6: Verification — sample label file
# ──────────────────────────────────────────────

def show_sample_labels():
    """Show a sample label file for manual verification."""
    print("\n" + "─" * 70)
    print("  SAMPLE LABEL FILE")
    print("─" * 70)

    # Find first label file in train
    train_labels_dir = OUTPUT_DIR / 'labels' / 'train'
    label_files = sorted(train_labels_dir.glob('*.txt'))
    if label_files:
        sample = label_files[0]
        print(f"\n  File: {sample.name}")
        print(f"  Image: {sample.stem}.JPG\n")
        with open(sample) as f:
            lines = f.readlines()
        for line in lines[:10]:
            parts = line.strip().split()
            if len(parts) == 5:
                cls, cx, cy, w, h = parts
                print(f"    class={cls} ({CLASS_NAMES[int(cls)]})  "
                      f"cx={cx}  cy={cy}  w={w}  h={h}")
        if len(lines) > 10:
            print(f"    ... ({len(lines)} total annotations)")
    else:
        print("  No label files found!")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 3B: CONVERT TO YOLO FORMAT")
    print("=" * 70)

    # Step 1: Parse
    print("\n📦 Step 1: Parsing crop filenames...")
    annotations = collect_all_annotations()
    print(f"  ✅ {len(annotations)} annotations parsed (categories 1-10)")

    # Step 2 & 3: Convert + split
    print("\n🔄 Step 2: Converting to YOLO format & splitting by planogram...")
    split_counts, split_ann_counts, split_cat_counts, issues, skipped = \
        build_yolo_dataset(annotations)

    # Step 4: data.yaml
    print("\n📝 Step 3: Writing data.yaml...")
    write_data_yaml()

    # Step 5: Summary
    print_summary(split_counts, split_ann_counts, split_cat_counts, issues, skipped)

    # Step 6: Sample
    show_sample_labels()

    # Final output structure
    print("\n" + "─" * 70)
    print("  OUTPUT STRUCTURE")
    print("─" * 70)
    for split in ['train', 'val', 'test']:
        img_count = len(list((OUTPUT_DIR / 'images' / split).glob('*')))
        lbl_count = len(list((OUTPUT_DIR / 'labels' / split).glob('*.txt')))
        print(f"  {split:>5}/  images: {img_count:>4}   labels: {lbl_count:>4}")

    print(f"\n  data.yaml: {OUTPUT_DIR / 'data.yaml'}")

    print("\n" + "=" * 70)
    print("  ✅ PHASE 3B COMPLETE!")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
