import os
import sys
from pathlib import Path
import io

sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.models.organization import Organization
from backend.app.models.store import Store
from backend.app.models.planogram import PlanogramVersion
from backend.app.models.audit import ShelfAudit, AuditStatus, AuditImage, ProcessingJob, JobStatus
from backend.app.models.compliance import ComplianceResult
from backend.app.models.review import HumanReview, ReviewStatus, MLTrainingSample
from backend.app.services.storage_service import storage
from backend.app.workers.pipeline import process_audit_pipeline, reprocess_audit_pipeline
from backend.app.workers.training_tasks import launch_training_task
import uuid

# --- MOCKING ML TO GUARANTEE HUMAN REVIEW ---
import backend.app.workers.pipeline as pipeline_module

def mock_yolo(image_bytes):
    return [{
        "class_id": 0, 
        "confidence": 0.85, 
        "bbox": [10, 10, 100, 100],
        "x": 10,
        "y": 10,
        "width": 90,
        "height": 90
    }]

def mock_recognition(image_bytes, detections):
    # Hardcode similarity to 0.20 to FORCE human review
    return [{
        "detection_index": 0,
        "predicted_sku_id": "SKU_001",
        "similarity": 0.20, 
        "margin": 0.05
    }]

pipeline_module.run_yolo_detection = mock_yolo
pipeline_module.run_recognition = mock_recognition


def run_demo():
    print("==============================================")
    print("   PHASE 12 FULL LIFECYCLE DEMONSTRATION")
    print("   (Using mocked ML to deterministically trigger HITL)")
    print("==============================================\n")
    
    db = SessionLocal()
    try:
        from backend.app.models.user import User
        user = db.query(User).first()
        if not user:
            print("Error: No users in DB.")
            return
            
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        from backend.app.models.planogram import Planogram
        plano_ver = db.query(PlanogramVersion).join(Planogram).filter(Planogram.organization_id == org.id).first()
        store = db.query(Store).filter(Store.organization_id == org.id).first()
        
        if not plano_ver or not store:
            # Fallback if the user's org has no data (e.g. they were seeded separately)
            org = db.query(Organization).first()
            plano_ver = db.query(PlanogramVersion).first()
            store = db.query(Store).first()
            # forcefully link user to this org just for the test
            user.organization_id = org.id
            db.commit()
        
        # 1. CREATE AUDIT
        audit = ShelfAudit(
            organization_id=org.id,
            store_id=store.id,
            planogram_version_id=plano_ver.id,
            status=AuditStatus.UPLOADED
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        
        # Dummy blank image
        from PIL import Image
        img = Image.new('RGB', (224, 224), color = 'red')
        img_bytes_io = io.BytesIO()
        img.save(img_bytes_io, format='JPEG')
        image_bytes = img_bytes_io.getvalue()
        
        storage_key = f"audits/{audit.id}/demo.jpg"
        storage.upload(io.BytesIO(image_bytes), storage_key, "image/jpeg")
        db.add(AuditImage(audit_id=audit.id, storage_key=storage_key))
        
        job = ProcessingJob(audit_id=audit.id, status=JobStatus.QUEUED)
        db.add(job)
        db.commit()
        
        print("1️⃣ UPLOADING SHELF IMAGE...")
        print(f"Created Audit: {audit.id}")
        
        # 2. RUN PIPELINE (WILL HALT)
        print("\n2️⃣ RUNNING ML PIPELINE...")
        process_audit_pipeline(audit.id, job.id)
        
        db.refresh(audit)
        print(f"Audit Status is now: {audit.status.name}")
        
        # 3. MANAGER REVIEWS VIA API
        from backend.app.auth.dependencies import get_current_user
        from backend.app.api.v1.reviews import resolve_review, ResolveReviewRequest, get_pending_reviews

        print("\n3️⃣ MANAGER REVIEWS UNCERTAIN DETECTION VIA API...")
        
        # 3.a Fetch pending reviews
        db.expire_all() # Ensure we see changes committed by process_audit_pipeline
        # Let's also make sure we only grab reviews for THIS audit to be safe
        pending = get_pending_reviews(db=db, current_user=user)
        pending = [p for p in pending if p.audit_id == audit.id]
        print(f"API Returned {len(pending)} pending reviews.")
        review_id = pending[0].id
        
        # 3.b Resolve review as new product
        resolve_payload = ResolveReviewRequest(
            is_new_product=True,
            new_product_name="Demo Energy Drink",
            new_product_brand="DemoBrand",
            new_product_category="Beverages"
        )
        print("Manager clicks 'Others / New Product' and creates a new product via API!")
        resp = resolve_review(review_id=review_id, req=resolve_payload, db=db, current_user=user)
        print(f"API Resolution Response: {resp}")
        
        # Fetch the newly generated product to verify SKU
        from backend.app.models.product import Product
        new_prod = db.query(Product).order_by(Product.created_at.desc()).first()
        print(f"API correctly generated new product {new_prod.sku_code} and saved crop as MLTrainingSample!")
        
        # 4. REPROCESS AUDIT & SHOW COMPLIANCE
        print("\n4️⃣ REPROCESSING AUDIT...")
        reprocess_audit_pipeline(audit.id)
        db.refresh(audit)
        
        print(f"Audit Status is now: {audit.status.name}")
        
        comp_result = db.query(ComplianceResult).filter(ComplianceResult.audit_id == audit.id).first()
        if comp_result:
            print("\n📊 COMPLIANCE REPORT GENERATED!")
            print(f" - Position Accuracy: {comp_result.position_accuracy * 100:.1f}%")
            print(f" - Availability Rate: {comp_result.availability_rate * 100:.1f}%")
            print(f" - Facing Compliance: {comp_result.facing_compliance * 100:.1f}%")
            
        # 5. RETRAINING BATCH
        print("\n5️⃣ BACKGROUND RETRAINING TASK...")
        settings.MIN_NEW_TRAINING_SAMPLES = 1 # Test configuration: Force it to run now
        print(f"Triggering PyTorch Triplet Loss fine-tuning (Requires {settings.MIN_NEW_TRAINING_SAMPLES} samples)...")
        
        # Provide a dummy negative catalogue image so triplet loss doesn't crash
        # The positive catalogue image is the one we just added above.
        # Negative image needs to be another product. Let's just upload a dummy one.
        from backend.app.models.product import Product, ProductImage
        neg_prod = db.query(Product).filter(Product.id != new_prod.id).first()
        if neg_prod:
            db.add(ProductImage(product_id=neg_prod.id, storage_key="dummy_neg.jpg", image_type="front"))
            storage.upload(io.BytesIO(image_bytes), "dummy_neg.jpg", "image/jpeg")
            db.commit()
            
        launch_training_task()
        
        print("\n✅ DEMO COMPLETE!")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_demo()
