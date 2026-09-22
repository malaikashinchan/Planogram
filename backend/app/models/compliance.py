import uuid
import enum
from sqlalchemy import Column, ForeignKey, Enum, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class ViolationType(str, enum.Enum):
    MISSING_PRODUCT = "MISSING_PRODUCT"
    EXTRA_PRODUCT = "EXTRA_PRODUCT"
    MISPLACED_PRODUCT = "MISPLACED_PRODUCT"
    FACING_MISMATCH = "FACING_MISMATCH"

class ComplianceResult(Base, TimestampMixin):
    __tablename__ = "compliance_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    position_accuracy = Column(Float, nullable=False)
    availability_rate = Column(Float, nullable=False)
    facing_compliance = Column(Float, nullable=False)

class ComplianceViolation(Base, TimestampMixin):
    __tablename__ = "compliance_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("shelf_audits.id", ondelete="CASCADE"), nullable=False, index=True)
    
    shelf_id = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    
    expected_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    actual_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    violation_type = Column(Enum(ViolationType), nullable=False)
