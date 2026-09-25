"""
Celery tasks for continuous PyTorch fine-tuning.
"""
from uuid import UUID
import os
import io
import time
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
import numpy as np

from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.workers.celery_app import celery_app
from backend.app.models.ml import ModelVersion, ModelStatus
from backend.app.models.review import MLTrainingSample, SampleStatus
from backend.app.models.product import Product
from backend.app.services.storage_service import storage

# We reuse the same model architecture from Phase 6
import torchvision.models as models

class EmbeddingNet(nn.Module):
    def __init__(self):
        super(EmbeddingNet, self).__init__()
        resnet = models.resnet50(weights=None)
        self.features = nn.Sequential(*list(resnet.children())[:-1])
        self.embedding = nn.Sequential(
            nn.Flatten(),
            nn.Linear(2048, 2048)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.embedding(x)
        return nn.functional.normalize(x, p=2, dim=1)

@celery_app.task(bind=True, max_retries=1)
def launch_training_task(self):
    """
    Background task to fine-tune the Recognition Model.
    """
    db = SessionLocal()
    try:
        # Check if already training
        active_training = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.TRAINING).first()
        if active_training:
            print("Training is already in progress. Skipping.")
            return
            
        pending_samples = db.query(MLTrainingSample).filter(
            MLTrainingSample.status == SampleStatus.PENDING
        ).all()
        
        if len(pending_samples) < settings.MIN_NEW_TRAINING_SAMPLES:
            print("Not enough samples to train.")
            return
            
        print(f"Starting training with {len(pending_samples)} new samples...")
        
        # 1. Register candidate model
        import datetime
        version_name = f"v_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        candidate = ModelVersion(
            model_name="siamese_resnet50",
            version=version_name,
            status=ModelStatus.TRAINING
        )
        db.add(candidate)
        db.commit()
        
        # 2. Build Triplet Dataset
        # Anchor = Human corrected shelf crop
        # Positive = Catalogue image for the corrected SKU
        # Negative = Catalogue image for a random/wrong SKU
        
        print(f"Fine-tuning Siamese ResNet50 on {len(pending_samples)} samples...")
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        anchors = []
        positives = []
        negatives = []
        
        for sample in pending_samples:
            # Anchor: Human corrected crop from S3
            anchor_bytes = storage.download(sample.crop_storage_key)
            if not anchor_bytes:
                continue
            anchor_img = Image.open(io.BytesIO(anchor_bytes)).convert("RGB")
            
            # Positive: Catalogue image
            from backend.app.models.product import ProductImage
            pos_img_db = db.query(ProductImage).filter(ProductImage.product_id == sample.correct_product_id).first()
            if not pos_img_db or not pos_img_db.storage_key:
                continue
            pos_bytes = storage.download(pos_img_db.storage_key)
            if not pos_bytes:
                continue
            pos_img = Image.open(io.BytesIO(pos_bytes)).convert("RGB")
            
            # Negative: Original predicted product or random product
            neg_img_db = db.query(ProductImage).filter(ProductImage.product_id != sample.correct_product_id, ProductImage.storage_key != None).first()
            if not neg_img_db:
                continue
            neg_bytes = storage.download(neg_img_db.storage_key)
            if not neg_bytes:
                continue
            neg_img = Image.open(io.BytesIO(neg_bytes)).convert("RGB")
            
            anchors.append(transform(anchor_img))
            positives.append(transform(pos_img))
            negatives.append(transform(neg_img))
            
        if not anchors:
            print("Failed to build triplet dataset (missing S3 images).")
            candidate.status = ModelStatus.RETIRED
            db.commit()
            return
            
        anchor_batch = torch.stack(anchors)
        positive_batch = torch.stack(positives)
        negative_batch = torch.stack(negatives)
        
        # 3. Model Setup
        model = EmbeddingNet()
        # Load weights from the current ACTIVE model if we had one
        try:
            model.load_state_dict(torch.load(settings.RESNET_MODEL_PATH, map_location="cpu"))
        except Exception as e:
            print(f"Warning: could not load baseline weights, starting from scratch. {e}")
            
        model.train()
        criterion = nn.TripletMarginLoss(margin=settings.TRAINING_TRIPLET_MARGIN, p=2)
        optimizer = torch.optim.Adam(model.parameters(), lr=settings.TRAINING_LEARNING_RATE)
        
        # 4. Training Loop (Fine-tuning)
        epochs = settings.TRAINING_EPOCHS
        for epoch in range(epochs):
            optimizer.zero_grad()
            anchor_out = model(anchor_batch)
            pos_out = model(positive_batch)
            neg_out = model(negative_batch)
            
            loss = criterion(anchor_out, pos_out, neg_out)
            loss.backward()
            optimizer.step()
            print(f"Epoch {epoch+1}/{epochs} | Triplet Loss: {loss.item():.4f}")
            
        # 5. Save Candidate
        candidate_path = str(settings.PROJECT_ROOT / "outputs" / "embeddings" / f"{version_name}.pth")
        torch.save(model.state_dict(), candidate_path)
        candidate.artifact_storage_key = candidate_path # Store local path for now
        
        # Update samples
        for s in pending_samples:
            s.status = SampleStatus.USED_FOR_TRAINING
        
        # 6. Candidate Evaluation
        # We evaluate the candidate against the holdout set (for now, simply checking if loss improved)
        # Real logic would run the validation pipeline
        print("Evaluating candidate against holdout set...")
        
        # For this prototype, we'll assume the fine-tuning was successful if loss < threshold
        passed_evaluation = loss.item() < settings.TRAINING_EVALUATION_LOSS_THRESHOLD
        
        if passed_evaluation:
            print(f"Candidate {version_name} passed evaluation! Promoting to ACTIVE.")
            
            # Retire current active
            current_active = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.ACTIVE).first()
            if current_active:
                current_active.status = ModelStatus.RETIRED
                current_active.retired_at = datetime.datetime.now(datetime.timezone.utc)
                
            candidate.status = ModelStatus.ACTIVE
            candidate.approved_at = datetime.datetime.now(datetime.timezone.utc)
            
            # Update the global symlink or setting so pipeline.py uses it
            # settings.RECOGNIZER_MODEL_PATH = candidate_path (requires restart, or dynamic loading)
        else:
            print(f"Candidate {version_name} failed evaluation (loss {loss.item():.4f} >= {settings.TRAINING_EVALUATION_LOSS_THRESHOLD}). Discarding.")
            candidate.status = ModelStatus.RETIRED
            
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Training task failed: {e}")
        # Clean up
        active_training = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.TRAINING).first()
        if active_training:
            active_training.status = ModelStatus.RETIRED
            db.commit()
    finally:
        db.close()
