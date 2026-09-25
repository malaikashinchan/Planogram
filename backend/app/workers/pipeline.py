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
from backend.app.core.config import settings
from backend.app.models.ml import RecognitionStatus
from backend.app.models.review import HumanReview
import time
import io
from PIL import Image

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

        # Fetch Expected positions from DB early to include their SKUs
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

        # Map SKUs to Product UUIDs for Recognitions, Reconstructions, and Compliance
        all_skus = {r["predicted_sku_id"] for r in recognitions if r.get("predicted_sku_id")}
        all_skus.update({p["sku_id"] for p in expected_planogram})
        
        products_db = db.query(Product).filter(
            Product.organization_id == audit.organization_id,
            Product.sku_code.in_(list(all_skus))
        ).all()
        sku_to_uuid = {p.sku_code: p.id for p in products_db}

        # Incremental Save: Recognitions
        has_uncertain_recognitions = False
        db_recognitions = []
        
        for idx, r in enumerate(recognitions):
            sku = r.get("predicted_sku_id")
            sim = r["similarity"]
            
            if sim >= settings.RECOGNITION_REVIEW_THRESHOLD:
                status = RecognitionStatus.AUTO_ACCEPTED
            else:
                status = RecognitionStatus.REVIEW_REQUIRED
                has_uncertain_recognitions = True
                
            rec = Recognition(
                detection_id=db_detections[r["detection_index"]].id,
                predicted_product_id=sku_to_uuid.get(sku) if sku else None,
                similarity=sim,
                margin=r["margin"],
                status=status
            )
            db.add(rec)
            db_recognitions.append((rec, r["detection_index"]))
        db.commit()
        
        if has_uncertain_recognitions:
            print(f"[Job {job_id}] Found uncertain recognitions. Flagging for Human Review...")
            img_pil = Image.open(io.BytesIO(image_bytes))
            
            for rec, det_idx in db_recognitions:
                if rec.status == RecognitionStatus.REVIEW_REQUIRED:
                    det = db_detections[det_idx]
                    bbox = (det.x1, det.y1, det.x2, det.y2)
                    crop_img = img_pil.crop(bbox)
                    
                    crop_bytes_io = io.BytesIO()
                    crop_img.save(crop_bytes_io, format="JPEG")
                    crop_bytes = crop_bytes_io.getvalue()
                    
                    crop_key = f"human_reviews/{audit_id}_{rec.id}.jpg"
                    storage.upload(io.BytesIO(crop_bytes), crop_key, "image/jpeg")
                    
                    hr = HumanReview(
                        organization_id=audit.organization_id,
                        audit_id=audit_id,
                        recognition_id=rec.id,
                        predicted_product_id=rec.predicted_product_id,
                        predicted_similarity=rec.similarity,
                        predicted_margin=rec.margin,
                        crop_storage_key=crop_key
                    )
                    db.add(hr)
            
            audit.status = AuditStatus.PENDING_REVIEW
            job.status = JobStatus.COMPLETED
            from datetime import datetime, timezone
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            print(f"[Job {job_id}] Audit {audit_id} halted for PENDING_REVIEW.")
            return # Halt early, waiting for human resolution

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
        
        # Expected positions were already fetched above
        
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
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=mp["shelf_id"], position=0, violation_type=ViolationType.MISSING_PRODUCT, expected_product_id=sku_to_uuid.get(mp.get("sku_id"))))
            
        for ep in compliance_data["extra_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=ep["shelf_id"], position=0, violation_type=ViolationType.EXTRA_PRODUCT, actual_product_id=sku_to_uuid.get(ep.get("sku_id"))))
            
        for mp in compliance_data["misplaced_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=mp["shelf_id"], position=mp["position"], violation_type=ViolationType.MISPLACED_PRODUCT, expected_product_id=sku_to_uuid.get(mp.get("expected_sku_id")), actual_product_id=sku_to_uuid.get(mp.get("actual_sku_id"))))
            
        for fv in compliance_data["facing_violations"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=fv["shelf_id"], position=0, violation_type=ViolationType.FACING_MISMATCH, expected_product_id=sku_to_uuid.get(fv.get("sku_id")), actual_product_id=sku_to_uuid.get(fv.get("sku_id"))))

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

def reprocess_audit_pipeline(audit_id: UUID):
    """
    Called after all HumanReviews are resolved.
    Runs reconstruction and compliance using the updated Recognitions.
    """
    db = SessionLocal()
    try:
        audit = db.query(ShelfAudit).filter(ShelfAudit.id == audit_id).first()
        if not audit:
            print(f"Audit {audit_id} not found.")
            return
            
        print(f"[Audit {audit_id}] Reprocessing after Human Reviews...")
        
        # 1. Fetch Detections and Recognitions
        db_detections = db.query(Detection).filter(Detection.audit_id == audit_id).order_by(Detection.created_at).all()
        
        # Build dictionaries for reconstruct_shelf
        detections_dict = []
        for d in db_detections:
            width = d.x2 - d.x1
            height = d.y2 - d.y1
            detections_dict.append({
                "class_id": d.class_id,
                "confidence": d.confidence,
                "bbox": [d.x1, d.y1, d.x2, d.y2],
                "x": d.x1,
                "y": d.y1,
                "width": width,
                "height": height
            })
            
        recognitions_dict = []
        from backend.app.models import Product
        
        for idx, d in enumerate(db_detections):
            rec = db.query(Recognition).filter(Recognition.detection_id == d.id).first()
            if rec:
                sku_code = None
                if rec.predicted_product_id:
                    prod = db.query(Product).filter(Product.id == rec.predicted_product_id).first()
                    if prod:
                        sku_code = prod.sku_code
                        
                recognitions_dict.append({
                    "detection_index": idx,
                    "predicted_sku_id": sku_code,
                    "similarity": rec.similarity,
                    "margin": rec.margin
                })
                
        # 2. Reconstruct Shelf
        reconstruction = reconstruct_shelf(detections_dict, recognitions_dict)
        
        # Delete old actual positions and compliance if any exist (safety)
        db.query(ActualShelfPosition).filter(ActualShelfPosition.audit_id == audit_id).delete()
        db.query(ComplianceViolation).filter(ComplianceViolation.audit_id == audit_id).delete()
        db.query(ComplianceResult).filter(ComplianceResult.audit_id == audit_id).delete()
        db.commit()
        
        # 3. Compliance Comparison prep (Fetch expected early)
        from backend.app.models import PlanogramPosition
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

        # Map SKUs to Product UUIDs again
        all_skus = {r["predicted_sku_id"] for r in recognitions_dict if r.get("predicted_sku_id")}
        all_skus.update({p["sku_id"] for p in expected_planogram})
        products_db = db.query(Product).filter(
            Product.organization_id == audit.organization_id,
            Product.sku_code.in_(list(all_skus))
        ).all()
        sku_to_uuid = {p.sku_code: p.id for p in products_db}
        
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
        
        # Expected planogram already fetched above
        
        compliance_data = calculate_compliance(reconstruction, expected_planogram)
        
        comp_result = ComplianceResult(
            audit_id=audit_id,
            position_accuracy=compliance_data["position_accuracy"],
            availability_rate=compliance_data["availability_rate"],
            facing_compliance=compliance_data["facing_compliance"]
        )
        db.add(comp_result)
        db.flush()
        
        for mp in compliance_data["missing_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=mp["shelf_id"], position=0, violation_type=ViolationType.MISSING_PRODUCT, expected_product_id=sku_to_uuid.get(mp.get("sku_id"))))
            
        for ep in compliance_data["extra_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=ep["shelf_id"], position=0, violation_type=ViolationType.EXTRA_PRODUCT, actual_product_id=sku_to_uuid.get(ep.get("sku_id"))))
            
        for mp in compliance_data["misplaced_products"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=mp["shelf_id"], position=mp["position"], violation_type=ViolationType.MISPLACED_PRODUCT, expected_product_id=sku_to_uuid.get(mp.get("expected_sku_id")), actual_product_id=sku_to_uuid.get(mp.get("actual_sku_id"))))
            
        for fv in compliance_data["facing_violations"]:
            db.add(ComplianceViolation(audit_id=audit_id, shelf_id=fv["shelf_id"], position=0, violation_type=ViolationType.FACING_MISMATCH, expected_product_id=sku_to_uuid.get(fv.get("sku_id")), actual_product_id=sku_to_uuid.get(fv.get("sku_id"))))
            
        # 4. Mark Audit Completed
        from datetime import datetime, timezone
        audit.status = AuditStatus.COMPLETED
        audit.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        print(f"[Audit {audit_id}] Reprocessing complete.")
        
    except Exception as e:
        db.rollback()
        print(f"Reprocessing failed for audit {audit_id}: {e}")
        raise
    finally:
        db.close()
