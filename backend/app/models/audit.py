import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class AuditStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobType(str, enum.Enum):
    ML_PIPELINE = "ML_PIPELINE"

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ShelfAudit(Base, TimestampMixin):
    __tablename__ = "shelf_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Must explicitly link to a VERSION, not the root planogram, for historical immutability
    planogram_version_id = Column(UUID(as_uuid=True), ForeignKey("planogram_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    status = Column(Enum(AuditStatus), default=AuditStatus.UPLOADED, nullable=False, index=True)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class AuditImage(Base, TimestampMixin):
    __tablename__ = "audit_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    
    storage_key = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    checksum = Column(String, nullable=True)

class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    
    job_type = Column(Enum(JobType), default=JobType.ML_PIPELINE, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    
    attempt_count = Column(Integer, default=0, nullable=False)
    error_message = Column(String, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
