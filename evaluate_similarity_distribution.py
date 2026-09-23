import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import glob
import time
import numpy as np
import matplotlib.pyplot as plt

from backend.app.ml.detection import run_yolo_detection
from backend.app.ml.recognition import run_recognition

# Get 20 random shelf images
img_paths = glob.glob("Dataset/GroceryDataset_part1/ShelfImages/*.JPG")[:20]

all_similarities = []

for idx, img_path in enumerate(img_paths):
    try:
        with open(img_path, "rb") as f:
            image_bytes = f.read()
        
        detections = run_yolo_detection(image_bytes)
        if not detections:
            continue
            
        recognitions = run_recognition(image_bytes, detections)
        for r in recognitions:
            all_similarities.append(r["similarity"])
            
        print(f"[{idx+1}/{len(img_paths)}] Processed {os.path.basename(img_path)}: found {len(recognitions)} items. (Avg Sim: {np.mean([r['similarity'] for r in recognitions]):.3f})")
    except Exception as e:
        print(f"Error on {img_path}: {e}")

if all_similarities:
    print(f"\n--- Distribution ---")
    print(f"Total crops: {len(all_similarities)}")
    print(f"Min: {np.min(all_similarities):.3f}")
    print(f"Max: {np.max(all_similarities):.3f}")
    print(f"Mean: {np.mean(all_similarities):.3f}")
    print(f"Median: {np.median(all_similarities):.3f}")
    
    # Plot histogram
    plt.figure(figsize=(10, 6))
    plt.hist(all_similarities, bins=50, color='skyblue', edgecolor='black')
    plt.axvline(x=0.6, color='red', linestyle='--', label='Original Arbitrary Threshold (0.6)')
    plt.title('Distribution of Cosine Similarities across 20 Shelf Images')
    plt.xlabel('Cosine Similarity')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(axis='y', alpha=0.75)
    
    # Save plot
    out_path = "similarity_distribution.png"
    plt.savefig(out_path)
    print(f"Saved plot to {out_path}")
else:
    print("No similarities collected.")

