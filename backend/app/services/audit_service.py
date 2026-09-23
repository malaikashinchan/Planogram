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
