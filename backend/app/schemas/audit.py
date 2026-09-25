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

class DetailedViolation(BaseModel):
    id: UUID
    shelf_id: str
    position: int
    violation_type: str
    expected_sku: str | None = None
    expected_name: str | None = None
    actual_sku: str | None = None
    actual_name: str | None = None

class AuditReviewResponse(BaseModel):
    review_id: UUID
    recognition_id: UUID
    crop_url: str
    predicted_sku: str | None = None
    predicted_name: str | None = None
    similarity: float | None = None
    margin: float | None = None
    corrected_sku: str | None = None
    corrected_name: str | None = None
    status: str
    reviewed_at: datetime | None = None


class JobResponse(BaseModel):
    status: str
    error_message: str | None = None


class AuditStoreResponse(BaseModel):
    id: UUID
    name: str

class AuditPlanogramResponse(BaseModel):
    id: UUID
    name: str

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
    compliance_score: float | None = None
    store: AuditStoreResponse | None = None
    planogram: AuditPlanogramResponse | None = None


class AuditDetailResponse(AuditResponse):
    image_url: str | None = None
    job: JobResponse | None = None
    compliance: ComplianceResponse | None = None
    violations: ViolationSummary | None = None
