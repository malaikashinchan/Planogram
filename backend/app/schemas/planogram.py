"""
Pydantic schemas for the Planograms API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Planogram (root) ──

class PlanogramCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    store_id: UUID | None = None


class PlanogramResponse(BaseModel):
    id: UUID
    organization_id: UUID
    store_id: UUID | None
    code: str
    name: str
    status: str
    created_by: UUID | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    positions_count: int = 0
    store: dict | None = None


# ── Planogram Version ──

class PositionInput(BaseModel):
    shelf_id: int = Field(ge=1)
    position: int = Field(ge=1)
    product_id: UUID


class PlanogramVersionCreate(BaseModel):
    positions: list[PositionInput] = Field(min_length=1)


class PositionResponse(BaseModel):
    id: UUID
    shelf_id: int
    position: int
    product_id: UUID


class PlanogramVersionResponse(BaseModel):
    id: UUID
    planogram_id: UUID
    version_number: int
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    created_by: UUID | None
    created_at: datetime | None = None
    positions: list[PositionResponse] = []
