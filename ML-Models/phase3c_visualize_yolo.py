"""
Phase 3C: Visualize YOLO Labels
===============================
Reads a subset of images and their corresponding YOLO label files from the
`dataset_yolo` directory, un-normalizes the coordinates, and draws bounding boxes
to visually verify that the YOLO conversion was correct.

Usage:
    python phase3c_visualize_yolo.py
"""

import os
import cv2
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
YOLO_DIR = BASE_DIR / "dataset_yolo"
OUTPUT_DIR = BASE_DIR / "outputs" / "yolo_verification"

CLASS_NAMES = {
    0: 'Cat-1',  1: 'Cat-2',  2: 'Cat-3',  3: 'Cat-4',  4: 'Cat-5',
    5: 'Cat-6',  6: 'Cat-7',  7: 'Cat-8',  8: 'Cat-9',  9: 'Cat-10',
}

CATEGORY_COLORS = {
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

CATEGORY_COLORS_RGB = {
    k: (v[2]/255, v[1]/255, v[0]/255) for k, v in CATEGORY_COLORS.items()
}

# ──────────────────────────────────────────────
# Un-normalize & Draw
# ──────────────────────────────────────────────

def draw_yolo_labels(image_path, label_path):
    """Draw YOLO labels on an image."""
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  ⚠ Could not read image {image_path}")
        return None

    h_img, w_img = img.shape[:2]
    
    if not label_path.exists():
        print(f"  ⚠ No label file found for {image_path.name}")
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
        x = (cx * w_img) - (w / 2)
        y = (cy * h_img) - (h / 2)
        
        x, y, w, h = int(x), int(y), int(w), int(h)
        
        color = CATEGORY_COLORS.get(class_id, (255, 255, 255))
        label = CLASS_NAMES.get(class_id, f"Cls-{class_id}")
        
        # Draw rectangle
        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)
        
        # Draw label background
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y = max(y - 4, text_h + 4)
        cv2.rectangle(
            img,
            (x, label_y - text_h - 4),
            (x + text_w + 4, label_y + 2),
            color, -1  # filled
        )
        
        # Draw label text (black on colored background)
        cv2.putText(
            img, label,
            (x + 2, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA
        )

    return img

def create_gallery(images, output_path, n_cols=3, n_rows=3):
    """Create a grid gallery of annotated images."""
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 14))
    fig.suptitle('Phase 3C: YOLO Verification Gallery', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    for idx, ax in enumerate(axes.flat):
        if idx < len(images):
            img_bgr, title = images[idx]
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            ax.imshow(img_rgb)
            ax.set_title(title, fontsize=8)
        ax.axis('off')
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color=CATEGORY_COLORS_RGB[i], linewidth=3, 
                   label=CLASS_NAMES[i])
        for i in range(10)
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=5, 
              fontsize=9, frameon=True, fancybox=True, shadow=True)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Gallery saved to: {output_path}")


def main():
    print("=" * 60)
    print("  PHASE 3C: VISUALIZE YOLO LABELS")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    images_to_show = []
    
    # Pick a few images from each split
    for split in ['train', 'val', 'test']:
        split_img_dir = YOLO_DIR / 'images' / split
        split_lbl_dir = YOLO_DIR / 'labels' / split
        
        if not split_img_dir.exists():
            continue
            
        img_files = list(split_img_dir.glob('*.JPG'))
        if not img_files:
            continue
            
        # Select up to 3 images per split to verify
        samples = random.sample(img_files, min(3, len(img_files)))
        
        for img_path in samples:
            lbl_path = split_lbl_dir / (img_path.stem + '.txt')
            print(f"  Processing [{split}] {img_path.name}")
            annotated_img = draw_yolo_labels(img_path, lbl_path)
            if annotated_img is not None:
                images_to_show.append((annotated_img, f"[{split}] {img_path.stem}"))
                
                # Optionally save individual images
                out_path = OUTPUT_DIR / f"{split}_{img_path.stem}_verified.jpg"
                cv2.imwrite(str(out_path), annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    
    if images_to_show:
        gallery_path = OUTPUT_DIR / "yolo_verification_gallery.png"
        create_gallery(images_to_show[:9], gallery_path)
        print(f"\n  ✅ Verification gallery created successfully!")
    else:
        print("\n  ⚠ No images processed.")
        

if __name__ == "__main__":
    main()
