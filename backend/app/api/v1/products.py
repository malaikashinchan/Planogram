"""
Product endpoints.

GET   /products                          — List products
POST  /products                          — Create product (ADMIN, MANAGER)
GET   /products/{product_id}             — Get product details
PATCH /products/{product_id}             — Update product (ADMIN, MANAGER)
PATCH /products/{product_id}/status      — Activate/deactivate (ADMIN, MANAGER)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models import User, Product
from backend.app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)
from backend.app.services import product_service


router = APIRouter(prefix="/products", tags=["Products"])


def _to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        organization_id=product.organization_id,
        sku_code=product.sku_code,
        name=product.name,
        brand=product.brand,
        category=product.category,
        barcode=product.barcode,
        status=product.status.value,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("/", response_model=list[ProductResponse])
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    products = product_service.get_products(
        db, current_user.organization_id, skip, limit
    )
    return [_to_response(p) for p in products]


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        product = product_service.create_product(
            db,
            current_user.organization_id,
            data.sku_code,
            data.name,
            data.brand,
            data.category,
            data.barcode,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return _to_response(product)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = product_service.get_product(
        db, product_id, current_user.organization_id
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return _to_response(product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    data: ProductUpdate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    try:
        product = product_service.update_product(
            db,
            product_id,
            current_user.organization_id,
            data.name,
            data.brand,
            data.category,
            data.barcode,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return _to_response(product)


@router.patch("/{product_id}/status", response_model=ProductResponse)
def update_product_status(
    product_id: UUID,
    data: ProductStatusUpdate,
    current_user: User = require_roles("ADMIN", "MANAGER"),
    db: Session = Depends(get_db),
):
    product = product_service.update_product_status(
        db, product_id, current_user.organization_id, data.status
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return _to_response(product)
