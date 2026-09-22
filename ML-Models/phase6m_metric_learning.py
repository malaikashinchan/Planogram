"""
Phase 6M: Target-Domain Metric Learning
=======================================
Instead of standard Cross-Entropy on a disjoint dataset, this script
trains a Siamese ResNet50 using Triplet Margin Loss directly on the
GroceryDataset domain.

Triplet Configuration:
- Anchor (A): A shelf crop from ProductImagesFromShelves
- Positive (P): A reference image from ProductImages (same brand)
- Negative (N): A reference image from ProductImages (different brand)

The model learns to embed A closer to P than to N, perfectly
mimicking our retrieval architecture.

Usage:
    python ML-Models/phase6m_metric_learning.py
"""

import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from pathlib import Path
import cv2
import copy
import time

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
CATALOGUE_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part1" / "ProductImages"
SHELF_CROPS_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part2" / "ProductImagesFromShelves"

OUTPUT_DIR = BASE_DIR / "outputs" / "metric_learning"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 32
EPOCHS = 10
LR = 1e-4
MARGIN = 1.0
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

TRANSFORMS_TRAIN = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

TRANSFORMS_VAL = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# ──────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────

class TripletGroceryDataset(Dataset):
    def __init__(self, anchor_paths, catalogue_map, transform=None):
        """
        anchor_paths: list of tuples (path, category_id)
        catalogue_map: dict {category_id: [list of reference image paths]}
        """
        self.anchor_paths = anchor_paths
        self.catalogue_map = catalogue_map
        self.transform = transform
        self.categories = list(catalogue_map.keys())

    def __len__(self):
        return len(self.anchor_paths)

    def __getitem__(self, idx):
        # Anchor
        anchor_path, anchor_cat = self.anchor_paths[idx]
        
        # Positive (random reference from same category)
        pos_path = random.choice(self.catalogue_map[anchor_cat])
        
        # Negative (random reference from different category)
        neg_cat = random.choice([c for c in self.categories if c != anchor_cat])
        neg_path = random.choice(self.catalogue_map[neg_cat])

        # Load images
        def load_img(p):
            img = cv2.imread(str(p))
            if img is None:
                raise ValueError(f"Failed to load {p}")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        img_a = load_img(anchor_path)
        img_p = load_img(pos_path)
        img_n = load_img(neg_path)

        if self.transform:
            img_a = self.transform(img_a)
            img_p = self.transform(img_p)
            img_n = self.transform(img_n)

        return img_a, img_p, img_n


def prepare_datasets():
    # 1. Build catalogue map
    catalogue_map = {}
    for cat_id in range(1, 11):
        cat_dir = CATALOGUE_DIR / str(cat_id)
        if cat_dir.exists():
            catalogue_map[cat_id] = list(cat_dir.glob('*.jpg'))
            
    # 2. Gather all anchor crops
    all_anchors = []
    for cat_id in range(1, 11):
        cat_dir = SHELF_CROPS_DIR / str(cat_id)
        if cat_dir.exists():
            for f in cat_dir.glob('*.png'):
                all_anchors.append((f, cat_id))
                
    # 3. Use all anchors for training
    random.seed(42)
    random.shuffle(all_anchors)
    
    print(f"Total Anchors (100% Train): {len(all_anchors)}")
    
    train_dataset = TripletGroceryDataset(all_anchors, catalogue_map, transform=TRANSFORMS_TRAIN)
    
    return train_dataset

# ──────────────────────────────────────────────
# Model Definition
# ──────────────────────────────────────────────

class EmbeddingNet(nn.Module):
    def __init__(self):
        super(EmbeddingNet, self).__init__()
        resnet = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        
        # Freeze Layer 1 & 2
        for name, param in resnet.named_parameters():
            if "layer1" in name or "layer2" in name or "conv1" in name or "bn1" in name:
                param.requires_grad = False
                
        # Remove FC layer to just output 2048-d feature map
        self.backbone = nn.Sequential(*list(resnet.children())[:-1])

    def forward(self, x):
        x = self.backbone(x)
        x = x.squeeze(-1).squeeze(-1) # Shape: (B, 2048)
        # L2 Normalize for Cosine Similarity retrieval
        x = nn.functional.normalize(x, p=2, dim=1)
        return x

# ──────────────────────────────────────────────
# Training Loop
# ──────────────────────────────────────────────

def train_model():
    print("=" * 60)
    print(" PHASE 6M: TARGET-DOMAIN METRIC LEARNING (TRIPLET LOSS)")
    print("=" * 60)

    train_ds = prepare_datasets()
    
    dataloaders = {
        'train': DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    }

    model = EmbeddingNet().to(DEVICE)
    criterion = nn.TripletMarginLoss(margin=MARGIN, p=2)
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=LR)

    best_loss = float('inf')

    print(f"\n🚀 Training on {DEVICE}...")

    for epoch in range(EPOCHS):
        print(f"\nEpoch {epoch+1}/{EPOCHS}")
        print("-" * 15)

        model.train()
        running_loss = 0.0
        print_freq = 10

        for i, (anc, pos, neg) in enumerate(dataloaders['train']):
            anc, pos, neg = anc.to(DEVICE), pos.to(DEVICE), neg.to(DEVICE)
            optimizer.zero_grad()

            embed_a = model(anc)
            embed_p = model(pos)
            embed_n = model(neg)

            loss = criterion(embed_a, embed_p, embed_n)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * anc.size(0)

            if (i + 1) % print_freq == 0:
                print(f"  Train Batch {i+1}/{len(dataloaders['train'])} - Triplet Loss: {loss.item():.4f}")

        epoch_loss = running_loss / len(dataloaders['train'].dataset)
        print(f"  TRAIN Summary: Average Triplet Loss: {epoch_loss:.4f}")

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            print("  🌟 New best training loss! Saving checkpoint...")
            torch.save(model.state_dict(), OUTPUT_DIR / "resnet50_triplet_best.pth")

    print("\n✅ Training Complete!")
    print(f"Best Training Triplet Loss: {best_loss:.4f}")

if __name__ == "__main__":
    train_model()
