"""
Audit endpoints (read-only for Phase 10).

GET /audits              — List audits
GET /audits/{audit_id}   — Get audit details with compliance + violations
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.models import User
from backend.app.schemas.audit import (
    AuditDetailResponse,
    AuditResponse,
    ComplianceResponse,
    ViolationSummary,
)
from backend.app.services import audit_service


router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get("/", response_model=list[AuditResponse])
def list_audits(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    audits = audit_service.get_audits(
        db, current_user.organization_id, skip, limit
    )

    return [
        AuditResponse(
            id=a.id,
            organization_id=a.organization_id,
            store_id=a.store_id,
            planogram_version_id=a.planogram_version_id,
            employee_id=a.employee_id,
            status=a.status.value,
            started_at=a.started_at,
            completed_at=a.completed_at,
            created_at=a.created_at,
        )
        for a in audits
    ]


@router.get("/{audit_id}", response_model=AuditDetailResponse)
def get_audit(
    audit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    audit = audit_service.get_audit(
        db, audit_id, current_user.organization_id
    )

    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found.",
        )

    # Build compliance
    compliance = None
    compliance_result = audit_service.get_compliance_result(db, audit.id)
    if compliance_result:
        compliance = ComplianceResponse(
            position_accuracy=compliance_result.position_accuracy,
            availability_rate=compliance_result.availability_rate,
            facing_compliance=compliance_result.facing_compliance,
        )

    # Build violation summary
    violations = None
    violation_data = audit_service.get_violation_summary(db, audit.id)
    if any(v > 0 for v in violation_data.values()):
        violations = ViolationSummary(**violation_data)

    return AuditDetailResponse(
        id=audit.id,
        organization_id=audit.organization_id,
        store_id=audit.store_id,
        planogram_version_id=audit.planogram_version_id,
        employee_id=audit.employee_id,
        status=audit.status.value,
        started_at=audit.started_at,
        completed_at=audit.completed_at,
        created_at=audit.created_at,
        compliance=compliance,
        violations=violations,
    )
