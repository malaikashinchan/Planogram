import logging
import cv2
import json
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path

logger = logging.getLogger(__name__)

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


class ProductRecognizer:
    def __init__(
        self,
        model_path: Path | str,
        ref_embeddings_path: Path | str,
        ref_labels_path: Path | str
    ):
        model_path = Path(model_path)
        ref_embeddings_path = Path(ref_embeddings_path)
        ref_labels_path = Path(ref_labels_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Metric model not found at: {model_path}")
        if not ref_embeddings_path.exists():
            raise FileNotFoundError(f"Reference embeddings not found at: {ref_embeddings_path}")
        if not ref_labels_path.exists():
            raise FileNotFoundError(f"Reference labels not found at: {ref_labels_path}")

        logger.info(f"Loading Triplet-Loss ResNet50 backbone from {model_path}")
        self.model = EmbeddingNet()
        state_dict = torch.load(str(model_path), map_location=DEVICE, weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()
        self.model.to(DEVICE)
        
        logger.info(f"Loading reference embeddings and labels")
        self.ref_embeddings = np.load(str(ref_embeddings_path))
        with open(ref_labels_path, 'r') as f:
            self.ref_labels = json.load(f)

    def recognize(self, image_data, detections: list[dict], batch_size: int = 64) -> list[dict]:
        """
        Runs recognition on a list of detections from YOLO.
        Returns a list of dicts with:
        {"detection_index": int, "predicted_sku_id": str, "category_id": int, "similarity": float, "margin": float}
        """
        if not detections:
            return []

        # Decode image if bytes
        if isinstance(image_data, bytes):
            np_arr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes.")
        else:
            img = image_data

        img_h, img_w = img.shape[:2]
        
        # Crop and transform
        tensors = []
        valid_indices = []
        for i, det in enumerate(detections):
            bbox = det["bbox"]
            x1, y1, x2, y2 = map(int, bbox)
            
            # Ensure within bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_w, x2), min(img_h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            crop = img[y1:y2, x1:x2]
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            try:
                tensors.append(TRANSFORM(crop_rgb))
                valid_indices.append(i)
            except Exception as e:
                logger.warning(f"Failed to transform crop {i}: {e}")
                continue
                
        if not tensors:
            return []

        all_embeddings = []
        # Process in batches
        for batch_start in range(0, len(tensors), batch_size):
            batch_end = min(batch_start + batch_size, len(tensors))
            batch_tensors = tensors[batch_start:batch_end]
            batch_input = torch.stack(batch_tensors).to(DEVICE)
            
            with torch.no_grad():
                features = self.model(batch_input)
            
            all_embeddings.append(features.cpu().numpy())
            
        query_embeddings = np.vstack(all_embeddings)
        
        # Calculate similarity (numpy matrix multiplication)
        sim_matrix = query_embeddings @ self.ref_embeddings.T
        
        results = []
        for q_idx, sims in enumerate(sim_matrix):
            original_det_idx = valid_indices[q_idx]
            
            top_indices = np.argsort(sims)[::-1][:5]  # Top 5
            
            top_matches = []
            for idx in top_indices:
                ref = self.ref_labels[idx]
                top_matches.append({
                    "category": ref["category"],
                    "similarity": float(sims[idx]),
                })

            brand_best = {}
            for m in top_matches:
                cat = m["category"]
                if cat not in brand_best or m["similarity"] > brand_best[cat]:
                    brand_best[cat] = m["similarity"]

            sorted_brands = sorted(brand_best.items(), key=lambda x: -x[1])
            top1_cat = sorted_brands[0][0]
            top1_sim = sorted_brands[0][1]
            top2_sim = sorted_brands[1][1] if len(sorted_brands) > 1 else 0.0
            margin = top1_sim - top2_sim
            
            sku_id = f"SKU_{str(top1_cat).zfill(3)}"
            
            results.append({
                "detection_index": original_det_idx,
                "predicted_sku_id": sku_id,
                "category_id": top1_cat,
                "similarity": top1_sim,
                "margin": margin
            })
            
        return results


# ── Global Singleton for Celery Worker ──

try:
    from backend.app.core.config import settings
    _recognizer_instance = ProductRecognizer(
        settings.RESNET_MODEL_PATH,
        settings.REFERENCE_EMBEDDINGS_PATH,
        settings.REFERENCE_LABELS_PATH
    )
except Exception as e:
    logger.error(f"Failed to load Recognizer components: {e}")
    _recognizer_instance = None


def run_recognition(image_bytes: bytes, detections: list[dict]) -> list[dict]:
    """
    Entry point for the ML pipeline. Uses the singleton recognizer.
    """
    if not _recognizer_instance:
        raise RuntimeError("Recognizer was not initialized successfully.")
    
    return _recognizer_instance.recognize(image_bytes, detections)
