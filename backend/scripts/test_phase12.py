import os
import sys
import uuid
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.core.database import SessionLocal
from backend.app.models.organization import Organization
from backend.app.models.planogram import PlanogramVersion
from backend.app.models.audit import ShelfAudit, AuditStatus, AuditImage, ProcessingJob, JobStatus
from backend.app.models.review import HumanReview, ReviewStatus
from backend.app.services.storage_service import storage
from backend.app.workers.pipeline import process_audit_pipeline

from backend.app.models.store import Store

def test_phase12(image_path_str):
    image_path = Path(image_path_str)
    if not image_path.exists():
        print(f"Error: Image {image_path} not found.")
        sys.exit(1)
        
    db = SessionLocal()
    try:
        # 1. Fetch dependencies
        org = db.query(Organization).first()
        if not org:
            print("Error: No organizations found. Did you run the Phase 7 seed script?")
            sys.exit(1)
            
        plano_ver = db.query(PlanogramVersion).first()
        if not plano_ver:
            print("Error: No planograms found.")
            sys.exit(1)
            
        store = db.query(Store).first()
        if not store:
            print("Error: No stores found.")
            sys.exit(1)
            
        print(f"Using Organization: {org.name}")
        print(f"Using Store: {store.name}")
        print(f"Using Planogram Version ID: {plano_ver.id} (v{plano_ver.version_number})")
        
        # 2. Create Audit
        audit = ShelfAudit(
            organization_id=org.id,
            store_id=store.id,
            planogram_version_id=plano_ver.id,
            status=AuditStatus.UPLOADED
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        
        # 3. Upload Image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        import io
        storage_key = f"audits/{audit.id}/{image_path.name}"
        storage.upload(io.BytesIO(image_bytes), storage_key, "image/jpeg")
        
        audit_img = AuditImage(
            audit_id=audit.id,
            storage_key=storage_key
        )
        db.add(audit_img)
        
        # 4. Create Job
        job = ProcessingJob(
            audit_id=audit.id,
            status=JobStatus.QUEUED
        )
        db.add(job)
        db.commit()
        
        print(f"\nCreated Audit: {audit.id}")
        print("Starting ML Pipeline (Synchronously for testing)...\n")
        
        # 5. Run Pipeline
        process_audit_pipeline(audit.id, job.id)
        
        # 6. Check Results
        db.refresh(audit)
        print(f"\n--- RESULTS FOR AUDIT {audit.id} ---")
        print(f"Final Audit Status: {audit.status.name}")
        
        if audit.status == AuditStatus.PENDING_REVIEW:
            print("✅ OUTCOME: Audit flagged for Human Review (Similarity < 0.40)")
            reviews = db.query(HumanReview).filter(
                HumanReview.audit_id == audit.id,
                HumanReview.status == ReviewStatus.PENDING
            ).all()
            print(f"Generated {len(reviews)} pending human review tasks:")
            for r in reviews:
                print(f" - Review Task {r.id}: Predicted Product = {r.predicted_product_id} | Similarity = {r.predicted_similarity:.3f}")
        elif audit.status == AuditStatus.COMPLETED:
            print("✅ OUTCOME: Audit completed automatically (All similarities >= 0.40)")
        else:
            print(f"⚠️ OUTCOME: Audit ended in unexpected state: {audit.status.name}")
            
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_phase12.py <path_to_image>")
        sys.exit(1)
        
    test_phase12(sys.argv[1])
