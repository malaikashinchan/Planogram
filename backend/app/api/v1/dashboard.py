from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.audit import ShelfAudit, AuditStatus
from backend.app.models.compliance import ComplianceResult
from backend.app.models.review import MLTrainingSample, SampleStatus
from backend.app.schemas.dashboard import (
    AuditStatisticsResponse,
    ComplianceTrendsResponse,
    DailyComplianceTrend,
    ModelStatusResponse
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/audit-statistics", response_model=AuditStatisticsResponse)
def get_audit_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Total audits last 7 days
    total_audits = db.query(ShelfAudit).filter(
        ShelfAudit.organization_id == org_id,
        ShelfAudit.created_at >= seven_days_ago
    ).count()
    
    # Average compliance score overall
    avg_compliance = db.query(func.avg(ComplianceResult.availability_rate)).join(
        ShelfAudit, ComplianceResult.audit_id == ShelfAudit.id
    ).filter(
        ShelfAudit.organization_id == org_id
    ).scalar()
    
    # Status breakdown
    status_counts = db.query(ShelfAudit.status, func.count(ShelfAudit.id)).filter(
        ShelfAudit.organization_id == org_id
    ).group_by(ShelfAudit.status).all()
    
    status_breakdown = {status.value: count for status, count in status_counts}
    
    return AuditStatisticsResponse(
        total_audits_last_7_days=total_audits,
        average_compliance_score=float(avg_compliance) if avg_compliance is not None else None,
        status_breakdown=status_breakdown
    )

@router.get("/compliance-trends", response_model=ComplianceTrendsResponse)
def get_compliance_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=29) # Last 30 days
    
    # Group by Date
    daily_avgs = db.query(
        func.date(ShelfAudit.created_at).label('date'),
        func.avg(ComplianceResult.availability_rate).label('avg_compliance')
    ).join(
        ShelfAudit, ComplianceResult.audit_id == ShelfAudit.id
    ).filter(
        ShelfAudit.organization_id == org_id,
        func.date(ShelfAudit.created_at) >= start_date,
        func.date(ShelfAudit.created_at) <= end_date
    ).group_by(
        func.date(ShelfAudit.created_at)
    ).all()
    
    avg_by_date = {row.date: float(row.avg_compliance) if row.avg_compliance else None for row in daily_avgs}
    
    trends = []
    for i in range(30):
        current_date = start_date + timedelta(days=i)
        trends.append(DailyComplianceTrend(
            date=current_date,
            average_compliance=avg_by_date.get(current_date, None)
        ))
        
    return ComplianceTrendsResponse(trends=trends)

@router.get("/model-status", response_model=ModelStatusResponse)
def get_model_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id
    
    pending_samples = db.query(MLTrainingSample).filter(
        MLTrainingSample.organization_id == org_id,
        MLTrainingSample.status == SampleStatus.PENDING
    ).count()
    
    return ModelStatusResponse(
        pending_training_samples=pending_samples,
        min_new_training_samples=settings.MIN_NEW_TRAINING_SAMPLES,
        recognition_review_threshold=settings.RECOGNITION_REVIEW_THRESHOLD,
        active_model_version="v1_baseline" # In a real system, you'd fetch this from a ModelRegistry table
    )
