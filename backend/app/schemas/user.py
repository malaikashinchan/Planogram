"""
Pydantic schemas for the Users API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    organization_id: UUID
    status: str
    email_verified: bool
    roles: list[str]
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class UserRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=50)


class UserStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ACTIVE|INACTIVE)$")
