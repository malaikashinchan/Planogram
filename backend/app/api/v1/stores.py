"""
Store endpoints.

GET   /stores                       — List stores
POST  /stores                       — Create store (ADMIN, MANAGER)
GET   /stores/{store_id}            — Get store details
PATCH /stores/{store_id}            — Update store (ADMIN, MANAGER)
PATCH /stores/{store_id}/status     — Activate/deactivate (ADMIN, MANAGER)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models import User, Store
from backend.app.schemas.store import (
    StoreCreate,
    StoreResponse,
    StoreStatusUpdate,
    StoreUpdate,
)
from backend.app.services import store_service


router = APIRouter(prefix="/stores", tags=["Stores"])


def _to_response(store: Store) -> StoreResponse:
    return StoreResponse(
        id=store.id,
        organization_id=store.organization_id,
        code=store.code,
        name=store.name,
        address=store.address,
        status=store.status.value,
        created_at=store.created_at,
        updated_at=store.updated_at,
    )


@router.get("/", response_model=list[StoreResponse])
def list_stores(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stores = store_service.get_stores(
        db, current_user.organization_id, skip, limit
    )
    return [_to_response(s) for s in stores]


@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    data: StoreCreate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        store = store_service.create_store(
            db,
            current_user.organization_id,
            data.code,
            data.name,
            data.address,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return _to_response(store)


@router.get("/{store_id}", response_model=StoreResponse)
def get_store(
    store_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = store_service.get_store(db, store_id, current_user.organization_id)

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found.",
        )

    return _to_response(store)


@router.patch("/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: UUID,
    data: StoreUpdate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    store = store_service.update_store(
        db, store_id, current_user.organization_id, data.name, data.address
    )

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found.",
        )

    return _to_response(store)


@router.patch("/{store_id}/status", response_model=StoreResponse)
def update_store_status(
    store_id: UUID,
    data: StoreStatusUpdate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    store = store_service.update_store_status(
        db, store_id, current_user.organization_id, data.status
    )

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found.",
        )

    return _to_response(store)
