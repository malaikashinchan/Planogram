"""
Phase 6J-A — Fine-Tune ResNet50 on Products-10K (Prototype Subset)
===================================================================
Trains a ResNet50 backbone on a controlled subset of the Products-10K dataset.

Strategy:
    - Select Top 2,000 most frequent classes (~50k images) to verify pipeline.
    - Map the 2,000 classes to indices 0..1999.
    - Split 80/20 into train and validation.
    - Load ResNet50 (ImageNet pretrained).
    - Freeze Layer 1 and Layer 2 (generic features).
    - Train Layer 3, Layer 4, and a new Linear(2048, 2000) classification head.
    - Save the best backbone (without the FC layer) for Phase 6K.

Usage:
    python phase6ja_finetune.py
"""

import os
import cv2
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from pathlib import Path
import time
import copy


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "Dataset" / "product_10k"
TRAIN_CSV = DATASET_DIR / "train.csv"
TRAIN_IMG_DIR = DATASET_DIR / "train" / "train"

OUTPUT_DIR = BASE_DIR / "outputs" / "finetune"

NUM_CLASSES = 2000
BATCH_SIZE = 64
EPOCHS = 10
PATIENCE = 3
LR = 1e-4

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# ──────────────────────────────────────────────
# Dataset Preparation
# ──────────────────────────────────────────────

class Product10kDataset(Dataset):
    def __init__(self, df, img_dir, transform=None):
        self.df = df.reset_index(drop=True)
        self.img_dir = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_name = row['name']
        label = row['mapped_class']

        img_path = str(self.img_dir / img_name)
        img = cv2.imread(img_path)
        
        if img is None:
            # Fallback for missing images - return a black image
            img = np.zeros((224, 224, 3), dtype=np.uint8)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if self.transform:
            img = self.transform(img)

        return img, label


def prepare_dataframes():
    """Load train.csv, filter to top 2000 classes, and split 80/20."""
    print("\n📦 Loading and preparing dataset...")
    df = pd.read_csv(TRAIN_CSV)
    
    # 1. Find top 2000 classes by frequency
    class_counts = df['class'].value_counts()
    top_classes = class_counts.head(NUM_CLASSES).index.tolist()
    
    # 2. Filter dataset
    df_subset = df[df['class'].isin(top_classes)].copy()
    
    # 3. Create continuous mapping 0..1999
    class_mapping = {old_id: new_id for new_id, old_id in enumerate(top_classes)}
    df_subset['mapped_class'] = df_subset['class'].map(class_mapping)
    
    # 4. Save mapping for reference
    mapping_df = pd.DataFrame([{"original_class": k, "mapped_class": v} for k, v in class_mapping.items()])
    mapping_df.to_csv(OUTPUT_DIR / "class_mapping.csv", index=False)
    
    # 5. Split Train/Val (80/20) - Stratified if possible, but random is fine for prototype
    # Shuffle first
    df_subset = df_subset.sample(frac=1, random_state=42).reset_index(drop=True)
    
    split_idx = int(len(df_subset) * 0.8)
    train_df = df_subset.iloc[:split_idx]
    val_df = df_subset.iloc[split_idx:]
    
    print(f"  Selected Top {NUM_CLASSES} classes")
    print(f"  Total subset images: {len(df_subset)}")
    print(f"  Train set: {len(train_df)} images")
    print(f"  Val set:   {len(val_df)} images")
    
    return train_df, val_df


# ──────────────────────────────────────────────
# Model Building
# ──────────────────────────────────────────────

def build_model(num_classes):
    """
    Load ResNet50, freeze Layer 1 & 2, replace FC layer.
    """
    print("\n🧠 Building ResNet50 model...")
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    
    # 1. Freeze everything first
    for param in model.parameters():
        param.requires_grad = False
        
    # 2. Unfreeze layer3 and layer4 (the deeper, task-specific features)
    for param in model.layer3.parameters():
        param.requires_grad = True
    for param in model.layer4.parameters():
        param.requires_grad = True
        
    # 3. Replace FC layer (automatically requires_grad=True)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)
    
    # Count trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Total parameters:     {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")
    
    model = model.to(DEVICE)
    return model


# ──────────────────────────────────────────────
# Training Loop
# ──────────────────────────────────────────────

def train_model(model, dataloaders, criterion, optimizer, num_epochs=10, patience=3):
    start_time = time.time()
    
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    epochs_no_improve = 0
    
    history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}

    print("\n🚀 Starting training...")

    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        print("-" * 15)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0
            
            # Print frequency
            print_freq = 10
            if print_freq == 0: print_freq = 1

            for i, (inputs, labels) in enumerate(dataloaders[phase]):
                inputs = inputs.to(DEVICE)
                labels = labels.to(DEVICE)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                
                # Progress logging
                if (i + 1) % print_freq == 0 or (i + 1) == len(dataloaders[phase]):
                    print(f"  {phase.capitalize()} Batch {i+1}/{len(dataloaders[phase])} - "
                          f"Loss: {loss.item():.4f}")

            epoch_loss = running_loss / len(dataloaders[phase].dataset)
            epoch_acc = running_corrects.float() / len(dataloaders[phase].dataset)
            
            history[f'{phase}_loss'].append(epoch_loss)
            history[f'{phase}_acc'].append(epoch_acc.item())

            print(f"  {phase.upper()} Summary: Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")

            if phase == 'val':
                if epoch_acc > best_acc:
                    best_acc = epoch_acc
                    best_model_wts = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                    print("  🌟 New best validation accuracy! Saving checkpoint...")
                    # Save backbone immediately
                    backbone = nn.Sequential(*list(model.children())[:-1])
                    torch.save(backbone.state_dict(), OUTPUT_DIR / "resnet50_product10k_subset.pth")
                else:
                    epochs_no_improve += 1

        if epochs_no_improve >= patience:
            print(f"\n🛑 Early stopping triggered after {epoch+1} epochs.")
            break

    time_elapsed = time.time() - start_time
    print(f"\nTraining complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s")
    print(f"Best Val Acc: {best_acc:4f}")

    # Load best model weights
    model.load_state_dict(best_model_wts)
    return model, history


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 6J-A: PROTOTYPE RESNET50 FINE-TUNING")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Prepare data
    train_df, val_df = prepare_dataframes()

    # Transforms (ImageNet standard)
    train_transforms = transforms.Compose([
        transforms.ToPILImage(),
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    val_transforms = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Datasets & Loaders
    train_dataset = Product10kDataset(train_df, TRAIN_IMG_DIR, train_transforms)
    val_dataset = Product10kDataset(val_df, TRAIN_IMG_DIR, val_transforms)

    dataloaders = {
        'train': DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0),
        'val': DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    }

    # 2. Build Model
    model = build_model(NUM_CLASSES)

    # 3. Training Setup
    criterion = nn.CrossEntropyLoss()
    # Only pass parameters that require grad to the optimizer
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=LR)

    # 4. Train
    model, history = train_model(model, dataloaders, criterion, optimizer, num_epochs=EPOCHS, patience=PATIENCE)

    # 5. Save backbone only (discard classification head)
    print("\n💾 Saving fine-tuned backbone...")
    
    # Create a fresh sequential model (same as phase 6D)
    backbone = nn.Sequential(*list(model.children())[:-1])
    
    save_path = OUTPUT_DIR / "resnet50_product10k_subset.pth"
    torch.save(backbone.state_dict(), save_path)
    print(f"  Saved backbone state dict to: {save_path}")
    
    # Save training history
    history_path = OUTPUT_DIR / "training_history.csv"
    pd.DataFrame(history).to_csv(history_path, index=False)
    print(f"  Saved training history to: {history_path}")

    print("\n" + "=" * 70)
    print("  ✅ PHASE 6J-A COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()
