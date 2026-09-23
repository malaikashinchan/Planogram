"""
The ML Pipeline orchestrator.
"""

from uuid import UUID

from backend.app.core.database import SessionLocal
from backend.app.models import (
    ShelfAudit, ProcessingJob, JobStatus, AuditImage,
    Detection, Recognition, ActualShelfPosition,
    ComplianceResult, ComplianceViolation, ViolationType, AuditStatus
)
from backend.app.services.storage_service import storage
from backend.app.ml.detection import run_yolo_detection
from backend.app.ml.recognition import run_recognition
from backend.app.ml.reconstruction import reconstruct_shelf
from backend.app.ml.compliance import calculate_compliance
import time

def process_audit_pipeline(audit_id: UUID, job_id: UUID):
    """
    Executes the full ML pipeline for a given audit.
    """
    db = SessionLocal()
    try:
        # 1. Fetch Job and update status
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            print(f"Job {job_id} not found.")
            return

        job.status = JobStatus.PROCESSING
        from datetime import datetime, timezone
        now_started = datetime.now(timezone.utc)
        job.started_at = now_started
        
        import time
        start_time = time.time()
        
        # 2. Fetch Audit & Image
        audit = db.query(ShelfAudit).filter(ShelfAudit.id == audit_id).first()
        if not audit:
            raise ValueError(f"Audit {audit_id} not found.")
        audit.started_at = now_started
        db.commit()
            
        audit_image = db.query(AuditImage).filter(AuditImage.audit_id == audit_id).first()
        if not audit_image:
            raise ValueError(f"No image found for Audit {audit_id}.")

        # 3. Download Image
        image_bytes = storage.download(audit_image.storage_key)
        if not image_bytes:
            raise ValueError("Failed to download image from storage.")

        # 4. YOLO Detection
        print(f"[Job {job_id}] Running YOLO detection...")
        yolo_start = time.time()
        detections = run_yolo_detection(image_bytes)
        print(f"[Job {job_id}] YOLO found {len(detections)} objects in {time.time() - yolo_start:.2f}s")
        
        # Incremental Save: Detections
        db_detections = []
        for d in detections:
            det = Detection(
                audit_id=audit_id,
                image_id=audit_image.id,
                class_id=d["class_id"],
                confidence=d["confidence"],
                x1=d["bbox"][0], y1=d["bbox"][1], x2=d["bbox"][2], y2=d["bbox"][3]
            )
            db_detections.append(det)
            db.add(det)
        db.commit()

        # 5. Product Recognition
        print(f"[Job {job_id}] Running product recognition...")
        recog_start = time.time()
        recognitions = run_recognition(image_bytes, detections)
        print(f"[Job {job_id}] Recognition matched {len(recognitions)} products in {time.time() - recog_start:.2f}s")

        # Map SKUs to Product UUIDs for Recognitions and Reconstructions
        all_skus = {r["predicted_sku_id"] for r in recognitions if r.get("predicted_sku_id")}
        from backend.app.models import Product
        products_db = db.query(Product).filter(
            Product.organization_id == audit.organization_id,
            Product.sku_code.in_(list(all_skus))
        ).all()
        sku_to_uuid = {p.sku_code: p.id for p in products_db}

        # Incremental Save: Recognitions
        for idx, r in enumerate(recognitions):
            sku = r.get("predicted_sku_id")
            rec = Recognition(
                detection_id=db_detections[r["detection_index"]].id,
                predicted_product_id=sku_to_uuid.get(sku) if sku else None,
                similarity=r["similarity"],
                margin=r["margin"]
            )
            db.add(rec)
        db.commit()

        # 6. Shelf Reconstruction
        print(f"[Job {job_id}] Reconstructing shelf...")
        recon_start = time.time()
        reconstruction = reconstruct_shelf(detections, recognitions)
        print(f"[Job {job_id}] Reconstructed shelf in {time.time() - recon_start:.2f}s")

        # Incremental Save: Actual Positions
        for shelf in reconstruction:
            for p in shelf["products"]:
                sku = p["sku_id"]
                if sku in sku_to_uuid:
                    pos = ActualShelfPosition(
                        audit_id=audit_id,
                        shelf_id=shelf["shelf_id"],
                        position=p["position"],
                        product_id=sku_to_uuid[sku],
                    )
                    db.add(pos)
        db.commit()

        # 7. Compliance Comparison
        print(f"[Job {job_id}] Calculating compliance...")
        comp_start = time.time()
        
        # Fetch Expected positions from DB
        from backend.app.models import PlanogramPosition, Product
        expected_positions_db = db.query(PlanogramPosition, Product).join(
            Product, PlanogramPosition.product_id == Product.id
        ).filter(
            PlanogramPosition.planogram_version_id == audit.planogram_version_id
        ).all()
        
        expected_planogram = [
            {
                "shelf_id": pos.shelf_id,
                "position": pos.position,
                "sku_id": prod.sku_code
            }
            for pos, prod in expected_positions_db
        ]
        
        compliance_data = calculate_compliance(reconstruction, expected_planogram)
        print(f"[Job {job_id}] Compliance calculated in {time.time() - comp_start:.2f}s")

        # Save Compliance Result
        comp_result = ComplianceResult(
            audit_id=audit_id,
            position_accuracy=compliance_data["position_accuracy"],
            availability_rate=compliance_data["availability_rate"],
            facing_compliance=compliance_data["facing_compliance"]
        )
        db.add(comp_result)
        db.flush()

        # Save Violations
        for mp in compliance_data["missing_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=mp["shelf_id"], position=0, violation_type=ViolationType.MISSING_PRODUCT))
            
        for ep in compliance_data["extra_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=ep["shelf_id"], position=0, violation_type=ViolationType.EXTRA_PRODUCT))
            
        for mp in compliance_data["misplaced_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=mp["shelf_id"], position=mp["position"], violation_type=ViolationType.MISPLACED_PRODUCT))
            
        for fv in compliance_data["facing_violations"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=fv["shelf_id"], position=0, violation_type=ViolationType.FACING_MISMATCH))

        # 8. Mark as complete
        from datetime import datetime, timezone
        now_completed = datetime.now(timezone.utc)
        job.status = JobStatus.COMPLETED
        job.completed_at = now_completed
        audit.status = AuditStatus.COMPLETED
        audit.completed_at = now_completed
        db.commit()
        
        print(f"[Job {job_id}] Audit {audit_id} fully processed in {time.time() - start_time:.2f}s")

    except Exception as e:
        db.rollback()
        # Handle failure
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            db.commit()
        print(f"Pipeline failed for audit {audit_id}: {e}")
        raise
    finally:
        db.close()
