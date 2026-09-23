"""
User endpoints.

GET   /users                    — List users in organization
GET   /users/{user_id}          — Get user details
PATCH /users/{user_id}/role     — Change user role (ADMIN)
PATCH /users/{user_id}/status   — Activate/deactivate user (ADMIN)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models import User
from backend.app.schemas.user import UserResponse, UserRoleUpdate, UserStatusUpdate
from backend.app.services import user_service


router = APIRouter(prefix="/users", tags=["Users"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        organization_id=user.organization_id,
        status=user.status.value,
        email_verified=user.email_verified_at is not None,
        roles=[r.name for r in user.roles],
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = user_service.get_users(
        db, current_user.organization_id, skip, limit, status_filter
    )
    return [_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = user_service.get_user(db, user_id, current_user.organization_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return _to_response(user)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    data: UserRoleUpdate,
    current_user: User = require_roles("ADMIN"),
    db: Session = Depends(get_db),
):
    try:
        user = user_service.update_user_role(
            db, user_id, current_user.organization_id, data.role
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return _to_response(user)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    current_user: User = require_roles("ADMIN"),
    db: Session = Depends(get_db),
):
    user = user_service.update_user_status(
        db, user_id, current_user.organization_id, data.status
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return _to_response(user)
