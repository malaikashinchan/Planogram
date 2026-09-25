"""
Pydantic schemas for the Products API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku_code: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=200)
    barcode: str | None = Field(default=None, max_length=100)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=200)
    barcode: str | None = Field(default=None, max_length=100)


class ProductResponse(BaseModel):
    id: UUID
    organization_id: UUID
    sku_code: str
    name: str
    brand: str | None
    category: str | None
    barcode: str | None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ACTIVE|INACTIVE)$")
