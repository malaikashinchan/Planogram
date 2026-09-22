import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    sku_code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    category = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("organization_id", "sku_code", name="uq_organization_sku"),
        UniqueConstraint("organization_id", "barcode", name="uq_organization_barcode"),
    )

class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    storage_key = Column(String, nullable=False)
    image_type = Column(String, nullable=False) # e.g. front, side, top
    checksum = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
