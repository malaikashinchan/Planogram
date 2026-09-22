import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class SampleStatus(str, enum.Enum):
    PENDING = "PENDING"
    INCLUDED_IN_DATASET = "INCLUDED_IN_DATASET"
    REJECTED = "REJECTED"

class HumanReview(Base, TimestampMixin):
    __tablename__ = "human_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recognition_id = Column(UUID(as_uuid=True), ForeignKey("recognitions.id", ondelete="RESTRICT"), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    predicted_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    correct_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    action = Column(String, nullable=False) # e.g. "CORRECTED", "CONFIRMED"
    notes = Column(String, nullable=True)

class MLTrainingSample(Base, TimestampMixin):
    __tablename__ = "ml_training_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    crop_storage_key = Column(String, nullable=False)
    correct_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    
    human_review_id = Column(UUID(as_uuid=True), ForeignKey("human_reviews.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(Enum(SampleStatus), default=SampleStatus.PENDING, nullable=False)
