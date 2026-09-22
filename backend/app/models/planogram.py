import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Integer, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class PlanogramStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class PlanogramVersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"

class Planogram(Base, TimestampMixin):
    __tablename__ = "planograms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=True, index=True)
    
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(Enum(PlanogramStatus), default=PlanogramStatus.ACTIVE, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_organization_planogram_code"),
    )

class PlanogramVersion(Base, TimestampMixin):
    __tablename__ = "planogram_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planogram_id = Column(UUID(as_uuid=True), ForeignKey("planograms.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    version_number = Column(Integer, nullable=False)
    status = Column(Enum(PlanogramVersionStatus), default=PlanogramVersionStatus.DRAFT, nullable=False)
    
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("planogram_id", "version_number", name="uq_planogram_version"),
    )

class PlanogramPosition(Base, TimestampMixin):
    __tablename__ = "planogram_positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planogram_version_id = Column(UUID(as_uuid=True), ForeignKey("planogram_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    shelf_id = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("planogram_version_id", "shelf_id", "position", name="uq_planogram_version_shelf_pos"),
    )
