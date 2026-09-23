"""
Pydantic schemas for the Audits API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ComplianceResponse(BaseModel):
    position_accuracy: float
    availability_rate: float
    facing_compliance: float


class ViolationSummary(BaseModel):
    missing: int = 0
    extra: int = 0
    misplaced: int = 0
    facing_mismatch: int = 0


class JobResponse(BaseModel):
    status: str
    error_message: str | None = None


class AuditResponse(BaseModel):
    id: UUID
    organization_id: UUID
    store_id: UUID
    planogram_version_id: UUID
    employee_id: UUID | None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class AuditDetailResponse(AuditResponse):
    job: JobResponse | None = None
    compliance: ComplianceResponse | None = None
    violations: ViolationSummary | None = None
