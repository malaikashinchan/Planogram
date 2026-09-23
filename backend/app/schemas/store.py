"""
Pydantic schemas for the Stores API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StoreCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)


class StoreResponse(BaseModel):
    id: UUID
    organization_id: UUID
    code: str
    name: str
    address: str | None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StoreStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ACTIVE|INACTIVE)$")
