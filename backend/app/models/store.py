import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class StoreStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

store_users = Table(
    "store_users",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("store_id", UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
)

class Store(Base, TimestampMixin):
    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    
    status = Column(Enum(StoreStatus), default=StoreStatus.ACTIVE, nullable=False)

    users = relationship("User", secondary=store_users, back_populates="stores")

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_organization_store_code"),
    )
