import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Float, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class ReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"

class SampleStatus(str, enum.Enum):
    PENDING = "PENDING"
    USED_FOR_TRAINING = "USED_FOR_TRAINING"
    REJECTED = "REJECTED"

class StorageStatus(str, enum.Enum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    AVAILABLE = "AVAILABLE"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"

class HumanReview(Base, TimestampMixin):
    __tablename__ = "human_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    recognition_id = Column(UUID(as_uuid=True), ForeignKey("recognitions.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    predicted_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    predicted_similarity = Column(Float, nullable=True)
    predicted_margin = Column(Float, nullable=True)
    
    crop_storage_key = Column(String, nullable=True)
    
    corrected_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    storage_status = Column(Enum(StorageStatus), default=StorageStatus.PENDING_UPLOAD, nullable=False)
    local_storage_path = Column(String, nullable=True)

class MLTrainingSample(Base, TimestampMixin):
    __tablename__ = "ml_training_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    crop_storage_key = Column(String, nullable=False)
    correct_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    
    human_review_id = Column(UUID(as_uuid=True), ForeignKey("human_reviews.id", ondelete="SET NULL"), nullable=True)
    
    # New storage status fields
    storage_status = Column(Enum(StorageStatus), default=StorageStatus.AVAILABLE, nullable=False)
    local_storage_path = Column(String, nullable=True)
    upload_attempts = Column(Integer, default=0, nullable=False)
    last_upload_error = Column(String, nullable=True)
    
    status = Column(Enum(SampleStatus), default=SampleStatus.PENDING, nullable=False)
