"""
Pydantic schemas for the Organizations API.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
