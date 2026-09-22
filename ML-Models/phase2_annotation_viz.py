"""
Phase 2: Annotation Visualization
==================================
Parses bounding box coordinates from crop filenames in GroceryDataset_part2,
maps them back to source shelf images in GroceryDataset_part1, draws annotated
bounding boxes with category labels, and generates a visual gallery + stats.

Usage:
    python phase2_annotation_viz.py
"""

import os
import re
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
from pathlib import Path


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent / "Dataset"
SHELF_IMAGES_DIR = BASE_DIR / "GroceryDataset_part1" / "ShelfImages"
PRODUCT_CROPS_DIR = BASE_DIR / "GroceryDataset_part2" / "ProductImagesFromShelves"
OUTPUT_DIR = BASE_DIR / "annotated_shelves"

# 10 distinct colors (BGR for OpenCV) — one per category
CATEGORY_COLORS = {
    1:  (0, 255, 0),       # Green
    2:  (255, 0, 0),       # Blue
    3:  (0, 0, 255),       # Red
    4:  (255, 255, 0),     # Cyan
    5:  (0, 255, 255),     # Yellow
    6:  (255, 0, 255),     # Magenta
    7:  (128, 255, 0),     # Lime
    8:  (0, 128, 255),     # Orange
    9:  (255, 128, 0),     # Sky Blue
    10: (128, 0, 255),     # Purple
}

CATEGORY_NAMES = {
    1: "Cat-1", 2: "Cat-2", 3: "Cat-3", 4: "Cat-4", 5: "Cat-5",
    6: "Cat-6", 7: "Cat-7", 8: "Cat-8", 9: "Cat-9", 10: "Cat-10",
}

# Matplotlib RGB colors (0-1 range) for the gallery legend
CATEGORY_COLORS_RGB = {
    k: (v[2]/255, v[1]/255, v[0]/255) for k, v in CATEGORY_COLORS.items()
}


# ──────────────────────────────────────────────
# Step 1: Parse crop filenames → annotations
# ──────────────────────────────────────────────

def parse_crop_filename(filename, category_id):
    """
    Parse a crop filename to extract source shelf image and bounding box.
    
    Filename format: C1_P01_N1_S3_1.JPG_1276_1828_276_448.png
    → source: C1_P01_N1_S3_1.JPG
    → bbox:   x=1276, y=1828, w=276, h=448
    """
    # Remove the .png extension
    name = filename.rsplit('.png', 1)[0]
    
    # Split from the right to get the 4 bbox numbers
    # The source image name contains underscores too, so we split from right
    parts = name.rsplit('_', 4)
    
    if len(parts) < 5:
        return None
    
    source_image = parts[0]  # e.g., "C1_P01_N1_S3_1.JPG"
    try:
        x = int(parts[1])
        y = int(parts[2])
        w = int(parts[3])
        h = int(parts[4])
    except ValueError:
        return None
    
    return {
        'source_image': source_image,
        'bbox': (x, y, w, h),
        'category_id': category_id,
        'crop_filename': filename,
    }


def collect_all_annotations():
    """Walk all category folders and parse every crop filename."""
    annotations = []
    
    for category_id in range(1, 11):  # Categories 1-10, skip 0 (background)
        cat_dir = PRODUCT_CROPS_DIR / str(category_id)
        if not cat_dir.exists():
            print(f"  ⚠ Category {category_id} folder not found, skipping")
            continue
        
        files = [f for f in os.listdir(cat_dir) if f.endswith('.png')]
        parsed_count = 0
        
        for fname in files:
            ann = parse_crop_filename(fname, category_id)
            if ann:
                annotations.append(ann)
                parsed_count += 1
        
        print(f"  Category {category_id:2d}: {parsed_count:4d} annotations parsed from {len(files)} files")
    
    return annotations


def group_by_shelf_image(annotations):
    """Group annotations by their source shelf image."""
    grouped = defaultdict(list)
    for ann in annotations:
        grouped[ann['source_image']].append(ann)
    return dict(grouped)


# ──────────────────────────────────────────────
# Step 2: Draw annotations on shelf images
# ──────────────────────────────────────────────

def draw_annotations(image, annotations, scale_factor=1.0):
    """
    Draw bounding boxes and labels on a shelf image.
    
    Args:
        image: numpy array (BGR)
        annotations: list of annotation dicts
        scale_factor: scaling for text/line thickness on high-res images
    """
    annotated = image.copy()
    h_img, w_img = annotated.shape[:2]
    
    # Scale line thickness and font based on image size
    thickness = max(2, int(2 * scale_factor))
    font_scale = max(0.4, 0.4 * scale_factor)
    
    for ann in annotations:
        x, y, w, h = ann['bbox']
        cat_id = ann['category_id']
        color = CATEGORY_COLORS.get(cat_id, (255, 255, 255))
        label = CATEGORY_NAMES.get(cat_id, f"Cat-{cat_id}")
        
        # Draw rectangle
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, thickness)
        
        # Draw label background
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y = max(y - 4, text_h + 4)
        cv2.rectangle(
            annotated,
            (x, label_y - text_h - 4),
            (x + text_w + 4, label_y + 2),
            color, -1  # filled
        )
        
        # Draw label text (black on colored background)
        cv2.putText(
            annotated, label,
            (x + 2, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA
        )
    
    return annotated


def annotate_all_images(grouped_annotations):
    """Annotate every shelf image that has matching crops and save to output dir."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    annotated_paths = []
    skipped = []
    
    total = len(grouped_annotations)
    
    for i, (shelf_name, annotations) in enumerate(sorted(grouped_annotations.items()), 1):
        shelf_path = SHELF_IMAGES_DIR / shelf_name
        
        if not shelf_path.exists():
            skipped.append(shelf_name)
            continue
        
        # Load image
        img = cv2.imread(str(shelf_path))
        if img is None:
            skipped.append(shelf_name)
            continue
        
        # Calculate scale factor based on image size
        h, w = img.shape[:2]
        scale_factor = max(w, h) / 1500.0
        
        # Draw annotations
        annotated = draw_annotations(img, annotations, scale_factor)
        
        # Save
        out_name = shelf_name.rsplit('.', 1)[0] + '_annotated.jpg'
        out_path = OUTPUT_DIR / out_name
        cv2.imwrite(str(out_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        annotated_paths.append(out_path)
        
        if i % 20 == 0 or i == total:
            print(f"  Annotated {i}/{total} images...")
    
    return annotated_paths, skipped


# ──────────────────────────────────────────────
# Step 3: Generate gallery overview
# ──────────────────────────────────────────────

def create_gallery(annotated_paths, output_path, n_cols=3, n_rows=3):
    """Create a grid gallery of sample annotated images."""
    # Pick evenly spaced samples
    n_samples = min(n_cols * n_rows, len(annotated_paths))
    if n_samples == 0:
        print("  ⚠ No annotated images to create gallery")
        return
    
    indices = np.linspace(0, len(annotated_paths) - 1, n_samples, dtype=int)
    samples = [annotated_paths[i] for i in indices]
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 14))
    fig.suptitle('Phase 2: Annotation Visualization — Sample Gallery', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    for idx, ax in enumerate(axes.flat):
        if idx < len(samples):
            img = cv2.imread(str(samples[idx]))
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax.imshow(img_rgb)
            ax.set_title(samples[idx].stem.replace('_annotated', ''), fontsize=8)
        ax.axis('off')
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color=CATEGORY_COLORS_RGB[i], linewidth=3, 
                   label=f"Category {i}")
        for i in range(1, 11)
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=5, 
              fontsize=9, frameon=True, fancybox=True, shadow=True)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Gallery saved to: {output_path}")


# ──────────────────────────────────────────────
# Step 4: Write statistics
# ──────────────────────────────────────────────

def write_stats(annotations, grouped, skipped, output_path):
    """Write annotation statistics to a text file."""
    cat_counts = Counter(ann['category_id'] for ann in annotations)
    anns_per_image = {k: len(v) for k, v in grouped.items()}
    
    with open(output_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("PHASE 2: ANNOTATION STATISTICS\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Total annotations parsed:     {len(annotations)}\n")
        f.write(f"Shelf images with annotations: {len(grouped)}\n")
        f.write(f"Shelf images skipped (not found): {len(skipped)}\n\n")
        
        f.write("─" * 40 + "\n")
        f.write("Annotations per Category\n")
        f.write("─" * 40 + "\n")
        for cat_id in sorted(cat_counts.keys()):
            f.write(f"  Category {cat_id:2d}: {cat_counts[cat_id]:5d} annotations\n")
        f.write(f"  {'TOTAL':>11s}: {sum(cat_counts.values()):5d}\n\n")
        
        f.write("─" * 40 + "\n")
        f.write("Annotations per Shelf Image\n")
        f.write("─" * 40 + "\n")
        counts = sorted(anns_per_image.values())
        f.write(f"  Min:    {min(counts):4d}\n")
        f.write(f"  Max:    {max(counts):4d}\n")
        f.write(f"  Mean:   {np.mean(counts):6.1f}\n")
        f.write(f"  Median: {np.median(counts):6.1f}\n\n")
        
        # Distribution
        f.write("─" * 40 + "\n")
        f.write("Top 10 most annotated images\n")
        f.write("─" * 40 + "\n")
        sorted_images = sorted(anns_per_image.items(), key=lambda x: x[1], reverse=True)
        for name, count in sorted_images[:10]:
            f.write(f"  {name:40s} → {count:3d} annotations\n")
        
        f.write("\n")
        f.write("─" * 40 + "\n")
        f.write("Bottom 10 least annotated images\n")
        f.write("─" * 40 + "\n")
        for name, count in sorted_images[-10:]:
            f.write(f"  {name:40s} → {count:3d} annotations\n")
        
        if skipped:
            f.write("\n")
            f.write("─" * 40 + "\n")
            f.write("Skipped images (shelf not found)\n")
            f.write("─" * 40 + "\n")
            for name in sorted(skipped):
                f.write(f"  {name}\n")
    
    print(f"  Stats saved to: {output_path}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("PHASE 2: ANNOTATION VISUALIZATION")
    print("=" * 60)
    
    # Step 1: Parse
    print("\n📦 Step 1: Parsing crop filenames...")
    annotations = collect_all_annotations()
    print(f"\n  ✅ Total annotations: {len(annotations)}")
    
    # Step 2: Group
    print("\n📊 Step 2: Grouping by shelf image...")
    grouped = group_by_shelf_image(annotations)
    print(f"  ✅ {len(grouped)} unique shelf images have annotations")
    
    # Step 3: Annotate
    print("\n🎨 Step 3: Drawing annotations on shelf images...")
    annotated_paths, skipped = annotate_all_images(grouped)
    print(f"  ✅ {len(annotated_paths)} images annotated")
    if skipped:
        print(f"  ⚠ {len(skipped)} images skipped (shelf image not found)")
    
    # Step 4: Gallery
    print("\n🖼️  Step 4: Generating gallery...")
    create_gallery(annotated_paths, OUTPUT_DIR / "gallery.png")
    
    # Step 5: Stats
    print("\n📈 Step 5: Writing statistics...")
    write_stats(annotations, grouped, skipped, OUTPUT_DIR / "annotation_stats.txt")
    
    print("\n" + "=" * 60)
    print("✅ PHASE 2 COMPLETE!")
    print(f"   Output directory: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
