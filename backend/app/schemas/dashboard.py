"""
Pydantic schemas for the Dashboard API.
"""

from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

class AuditStatisticsResponse(BaseModel):
    total_audits_last_7_days: int
    average_compliance_score: float | None
    status_breakdown: dict[str, int]

class DailyComplianceTrend(BaseModel):
    date: date
    average_compliance: float | None

class ComplianceTrendsResponse(BaseModel):
    trends: List[DailyComplianceTrend]

class ModelStatusResponse(BaseModel):
    pending_training_samples: int
    min_new_training_samples: int
    recognition_review_threshold: float
    active_model_version: str | None
    is_training: bool = False
    last_training_date: datetime | None = None
