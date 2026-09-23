"""
Organization endpoints.

GET   /organizations/me  — View current user's organization
PATCH /organizations/me  — Update organization name (ADMIN only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models import User
from backend.app.schemas.organization import OrganizationResponse, OrganizationUpdate
from backend.app.services import organization_service


router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db, current_user.organization_id)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value,
    )


@router.patch("/me", response_model=OrganizationResponse)
def update_my_organization(
    data: OrganizationUpdate,
    current_user: User = require_roles("ADMIN"),
    db: Session = Depends(get_db),
):
    org = organization_service.update_organization(
        db, current_user.organization_id, data.name
    )

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value,
    )
