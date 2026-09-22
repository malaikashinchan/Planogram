import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Float, Integer, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class ModelStatus(str, enum.Enum):
    TRAINING = "TRAINING"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"

class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable so it can be a global model or org-specific
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True)
    
    model_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    artifact_storage_key = Column(String, nullable=True)
    
    status = Column(Enum(ModelStatus), default=ModelStatus.TRAINING, nullable=False)
    metrics = Column(JSONB, nullable=True)
    
    approved_at = Column(DateTime(timezone=True), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "model_name", "version", name="uq_model_version"),
    )

class Detection(Base, TimestampMixin):
    __tablename__ = "detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("audit_images.id", ondelete="CASCADE"), nullable=True, index=True)
    
    class_id = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Bounding box coordinates
    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)
    x2 = Column(Float, nullable=False)
    y2 = Column(Float, nullable=False)
    
    crop_storage_key = Column(String, nullable=True)

class Recognition(Base, TimestampMixin):
    __tablename__ = "recognitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("detections.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    predicted_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    similarity = Column(Float, nullable=False)
    margin = Column(Float, nullable=True)
    
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True)

class ActualShelfPosition(Base, TimestampMixin):
    __tablename__ = "actual_shelf_positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    
    shelf_id = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Traceability links
    detection_id = Column(UUID(as_uuid=True), ForeignKey("detections.id", ondelete="SET NULL"), nullable=True)
    recognition_id = Column(UUID(as_uuid=True), ForeignKey("recognitions.id", ondelete="SET NULL"), nullable=True)
    
    center_x = Column(Float, nullable=True)
    center_y = Column(Float, nullable=True)
