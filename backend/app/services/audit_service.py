"""
Business logic for Audits — with organization isolation.

Phase 10: Read-only access to existing audit records.
Phase 11: Audit creation + ML processing pipeline.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import ShelfAudit, ComplianceResult, ComplianceViolation, ViolationType


def get_audits(
    db: Session,
    organization_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[ShelfAudit]:
    """List audits within the organization, newest first."""
    return list(
        db.scalars(
            select(ShelfAudit)
            .where(ShelfAudit.organization_id == organization_id)
            .order_by(ShelfAudit.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )


def get_audit(
    db: Session,
    audit_id: UUID,
    organization_id: UUID,
) -> ShelfAudit | None:
    """Get a single audit, scoped to organization."""
    return db.scalar(
        select(ShelfAudit).where(
            ShelfAudit.id == audit_id,
            ShelfAudit.organization_id == organization_id,
        )
    )


def get_processing_job(
    db: Session,
    audit_id: UUID,
) -> ProcessingJob | None:
    """Get the processing job associated with an audit."""
    from backend.app.models import ProcessingJob
    return db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.audit_id == audit_id,
        )
    )


def get_compliance_result(
    db: Session,
    audit_id: UUID,
) -> ComplianceResult | None:
    """Get the compliance result for an audit."""
    return db.scalar(
        select(ComplianceResult).where(
            ComplianceResult.audit_id == audit_id,
        )
    )


def get_violation_summary(
    db: Session,
    audit_id: UUID,
) -> dict[str, int]:
    """
    Count violations by type for an audit.
    Returns: {"missing": N, "extra": N, "misplaced": N, "facing_mismatch": N}
    """
    violations = list(
        db.scalars(
            select(ComplianceViolation).where(
                ComplianceViolation.audit_id == audit_id,
            )
        ).all()
    )

    summary = {
        "missing": 0,
        "extra": 0,
        "misplaced": 0,
        "facing_mismatch": 0,
    }

    for v in violations:
        if v.violation_type == ViolationType.MISSING_PRODUCT:
            summary["missing"] += 1
        elif v.violation_type == ViolationType.EXTRA_PRODUCT:
            summary["extra"] += 1
        elif v.violation_type == ViolationType.MISPLACED_PRODUCT:
            summary["misplaced"] += 1
        elif v.violation_type == ViolationType.FACING_MISMATCH:
            summary["facing_mismatch"] += 1

    return summary


def create_audit(
    db: Session,
    organization_id: UUID,
    employee_id: UUID,
    store_id: UUID,
    planogram_version_id: UUID,
    image_file_obj,
    image_filename: str,
    image_content_type: str,
    image_size: int,
) -> tuple[ShelfAudit, ProcessingJob]:
    from backend.app.models import Store, PlanogramVersion, Planogram, AuditImage, ProcessingJob, AuditStatus, JobStatus
    from backend.app.services.storage_service import storage
    import uuid

    # 1. Verify Store
    store = db.scalar(
        select(Store).where(Store.id == store_id, Store.organization_id == organization_id)
    )
    if not store:
        raise ValueError("Store not found in organization.")

    # 2. Verify PlanogramVersion
    pv = db.scalar(
        select(PlanogramVersion)
        .join(Planogram)
        .where(
            PlanogramVersion.id == planogram_version_id,
            Planogram.organization_id == organization_id,
        )
    )
    if not pv:
        raise ValueError("Planogram version not found in organization.")

    # 3. Create Audit
    audit = ShelfAudit(
        organization_id=organization_id,
        store_id=store_id,
        planogram_version_id=planogram_version_id,
        employee_id=employee_id,
        status=AuditStatus.PROCESSING,
    )
    db.add(audit)
    db.flush()

    # 4. Upload Image
    storage_key = f"organizations/{organization_id}/audits/{audit.id}/{uuid.uuid4()}.jpg"
    success = storage.upload(image_file_obj, storage_key, image_content_type)
    if not success:
        db.rollback()
        raise ValueError("Failed to upload image to storage.")

    # 5. Create AuditImage
    audit_image = AuditImage(
        audit_id=audit.id,
        storage_key=storage_key,
        mime_type=image_content_type,
        file_size=image_size,
    )
    db.add(audit_image)
    
    # 6. Create ProcessingJob
    job = ProcessingJob(
        audit_id=audit.id,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(audit)
    db.refresh(job)

    return audit, job

