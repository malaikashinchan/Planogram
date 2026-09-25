"""
Planogram endpoints.

GET  /planograms                                              — List planograms
POST /planograms                                              — Create planogram (ADMIN, MANAGER)
GET  /planograms/{planogram_id}                               — Get planogram
GET  /planograms/{planogram_id}/versions                      — List versions
POST /planograms/{planogram_id}/versions                      — Create version (ADMIN, MANAGER)
GET  /planograms/{planogram_id}/versions/{version_id}         — Get specific version
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Form
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models import User, Planogram, PlanogramVersion, Store
from backend.app.schemas.planogram import (
    PlanogramCreate,
    PlanogramResponse,
    PlanogramVersionCreate,
    PlanogramVersionResponse,
    PositionResponse,
)
from backend.app.services import planogram_service


router = APIRouter(prefix="/planograms", tags=["Planograms"])


def _planogram_response(p: Planogram, positions_count: int = 0, store: dict | None = None) -> PlanogramResponse:
    return PlanogramResponse(
        id=p.id,
        organization_id=p.organization_id,
        store_id=p.store_id,
        code=p.code,
        name=p.name,
        status=p.status.value,
        created_by=p.created_by,
        created_at=p.created_at,
        updated_at=p.updated_at,
        positions_count=positions_count,
        store=store,
    )


def _version_response(
    v: PlanogramVersion,
    positions: list | None = None,
) -> PlanogramVersionResponse:
    pos_list = []
    if positions:
        pos_list = [
            PositionResponse(
                id=p.id,
                shelf_id=p.shelf_id,
                position=p.position,
                product_id=p.product_id,
            )
            for p in positions
        ]

    return PlanogramVersionResponse(
        id=v.id,
        planogram_id=v.planogram_id,
        version_number=v.version_number,
        status=v.status.value,
        effective_from=v.effective_from,
        effective_to=v.effective_to,
        published_at=v.published_at,
        created_by=v.created_by,
        created_at=v.created_at,
        positions=pos_list,
    )


# ── Root Planogram Endpoints ──


@router.get("/", response_model=list[PlanogramResponse])
def list_planograms(
    store_id: UUID | None = Query(None, description="Filter by store ID"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    planograms = planogram_service.get_planograms(
        db, current_user.organization_id, skip, limit, store_id
    )
    
    result = []
    for p in planograms:
        # Get active or latest version
        versions = planogram_service.get_versions(db, p.id, current_user.organization_id)
        pos_count = 0
        if versions:
            latest_version = versions[-1] # Usually the most recently created or published
            positions = planogram_service.get_positions_for_version(db, latest_version.id)
            pos_count = len(positions)
            
        store_info = None
        if p.store_id:
            store = db.query(Store).filter(Store.id == p.store_id).first()
            if store:
                store_info = {"id": str(store.id), "name": store.name}
            
        result.append(_planogram_response(p, pos_count, store_info))
        
    return result


@router.post("/", response_model=PlanogramResponse, status_code=status.HTTP_201_CREATED)
def create_planogram(
    data: PlanogramCreate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        planogram = planogram_service.create_planogram(
            db,
            current_user.organization_id,
            current_user.id,
            data.code,
            data.name,
            data.store_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return _planogram_response(planogram)


@router.delete("/{planogram_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planogram(
    planogram_id: UUID,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        planogram_service.delete_planogram(
            db, planogram_id, current_user.organization_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/upload", response_model=PlanogramVersionResponse, status_code=status.HTTP_201_CREATED)
def upload_planogram(
    name: str | None = Form(None),
    store_id: UUID | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        version = planogram_service.ingest_planogram(
            db,
            current_user.organization_id,
            current_user.id,
            file,
            store_uuid=store_id,
            name=name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    positions = planogram_service.get_positions_for_version(db, version.id)
    return _version_response(version, positions)


@router.get("/{planogram_id}", response_model=PlanogramResponse)
def get_planogram(
    planogram_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    planogram = planogram_service.get_planogram(
        db, planogram_id, current_user.organization_id
    )

    if not planogram:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planogram not found.",
        )

    versions = planogram_service.get_versions(db, planogram.id, current_user.organization_id)
    pos_count = 0
    if versions:
        latest_version = versions[-1]
        positions = planogram_service.get_positions_for_version(db, latest_version.id)
        pos_count = len(positions)

    store_info = None
    if planogram.store_id:
        store = db.query(Store).filter(Store.id == planogram.store_id).first()
        if store:
            store_info = {"id": str(store.id), "name": store.name}

    return _planogram_response(planogram, pos_count, store_info)


# ── Version Endpoints ──


@router.get("/{planogram_id}/versions", response_model=list[PlanogramVersionResponse])
def list_versions(
    planogram_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify planogram exists in org
    planogram = planogram_service.get_planogram(
        db, planogram_id, current_user.organization_id
    )
    if not planogram:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planogram not found.",
        )

    versions = planogram_service.get_versions(
        db, planogram_id, current_user.organization_id
    )

    result = []
    for v in versions:
        positions = planogram_service.get_positions_for_version(db, v.id)
        result.append(_version_response(v, positions))

    return result


@router.post(
    "/{planogram_id}/versions",
    response_model=PlanogramVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    planogram_id: UUID,
    data: PlanogramVersionCreate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    positions_dicts = [
        {
            "shelf_id": p.shelf_id,
            "position": p.position,
            "product_id": p.product_id,
        }
        for p in data.positions
    ]

    try:
        version = planogram_service.create_version(
            db,
            planogram_id,
            current_user.organization_id,
            current_user.id,
            positions_dicts,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    positions = planogram_service.get_positions_for_version(db, version.id)
    return _version_response(version, positions)


@router.get(
    "/{planogram_id}/versions/{version_id}",
    response_model=PlanogramVersionResponse,
)
def get_version(
    planogram_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    version = planogram_service.get_version(
        db, planogram_id, version_id, current_user.organization_id
    )

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planogram version not found.",
        )

    positions = planogram_service.get_positions_for_version(db, version.id)
    return _version_response(version, positions)
