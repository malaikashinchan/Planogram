import cv2
import json
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path

BASE_DIR = Path("/Users/as-mac-1311/Downloads/Planogram")
CATALOGUE_DIR = BASE_DIR / "Dataset" / "GroceryDataset_part1" / "ProductImages"
OUTPUT_DIR = BASE_DIR / "outputs" / "embeddings"
MODEL_PATH = BASE_DIR / "outputs" / "metric_learning" / "resnet50_triplet_best.pth"

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

class EmbeddingNet(nn.Module):
    def __init__(self):
        super(EmbeddingNet, self).__init__()
        resnet = models.resnet50(weights=None)
        self.backbone = nn.Sequential(*list(resnet.children())[:-1])

    def forward(self, x):
        x = self.backbone(x)
        x = x.squeeze(-1).squeeze(-1)
        x = nn.functional.normalize(x, p=2, dim=1)
        return x

def get_catalogue_paths():
    paths = []
    labels = []
    if not CATALOGUE_DIR.exists():
        return paths, labels
    for p in CATALOGUE_DIR.rglob("*.jpg"):
        try:
            brand_id = p.parent.name
            brand_idx = int(brand_id.replace("B", ""))
            labels.append({
                "category": brand_idx,
                "brand_id": brand_id,
                "sku_id": f"SKU_{str(brand_idx).zfill(3)}",
                "filename": p.name
            })
            paths.append(p)
        except Exception:
            continue
    return paths, labels

def main():
    print(f"Loading Triplet-Loss ResNet50 backbone from {MODEL_PATH}")
    model = EmbeddingNet()
    state_dict = torch.load(str(MODEL_PATH), map_location=DEVICE, weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    model.to(DEVICE)

    paths, labels = get_catalogue_paths()
    print(f"Found {len(paths)} reference images.")

    all_embeddings = []
    failed = 0
    BATCH_SIZE = 64

    for batch_start in range(0, len(paths), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(paths))
        batch_paths = paths[batch_start:batch_end]

        batch_tensors = []
        for p in batch_paths:
            img = cv2.imread(str(p))
            if img is None:
                failed += 1
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            batch_tensors.append(TRANSFORM(img_rgb))

        if not batch_tensors:
            continue

        batch_input = torch.stack(batch_tensors).to(DEVICE)
        with torch.no_grad():
            features = model(batch_input)
        all_embeddings.append(features.cpu().numpy())
        
        print(f"Processed {batch_end}/{len(paths)}")

    if not all_embeddings:
        print("No embeddings generated!")
        return

    embeddings = np.vstack(all_embeddings)
    print(f"Saved: reference_embeddings.npy ({embeddings.shape})")
    
    np.save(str(OUTPUT_DIR / "reference_embeddings.npy"), embeddings)
    with open(OUTPUT_DIR / "reference_labels.json", "w") as f:
        json.dump(labels, f, indent=4)
    print("Done!")

if __name__ == "__main__":
    main()
