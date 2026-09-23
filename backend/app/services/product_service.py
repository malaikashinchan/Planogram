"""
Business logic for Products — with organization isolation.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Product, ProductStatus


def get_products(
    db: Session,
    organization_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Product]:
    """List products within the organization."""
    return list(
        db.scalars(
            select(Product)
            .where(Product.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        ).all()
    )


def get_product(
    db: Session,
    product_id: UUID,
    organization_id: UUID,
) -> Product | None:
    """Get a single product, scoped to organization."""
    return db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.organization_id == organization_id,
        )
    )


def create_product(
    db: Session,
    organization_id: UUID,
    sku_code: str,
    name: str,
    brand: str | None = None,
    category: str | None = None,
    barcode: str | None = None,
) -> Product:
    """Create a new product. Raises ValueError on duplicate SKU or barcode."""
    product = Product(
        organization_id=organization_id,
        sku_code=sku_code.strip(),
        name=name.strip(),
        brand=brand.strip() if brand else None,
        category=category.strip() if category else None,
        barcode=barcode.strip() if barcode else None,
        status=ProductStatus.ACTIVE,
    )

    db.add(product)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        error_msg = str(exc.orig)
        if "uq_organization_sku" in error_msg:
            raise ValueError(
                f"A product with SKU '{sku_code}' already exists in your organization."
            )
        elif "uq_organization_barcode" in error_msg:
            raise ValueError(
                f"A product with barcode '{barcode}' already exists in your organization."
            )
        raise ValueError("A product with these details already exists.")

    db.refresh(product)
    return product


def update_product(
    db: Session,
    product_id: UUID,
    organization_id: UUID,
    name: str | None = None,
    brand: str | None = None,
    category: str | None = None,
    barcode: str | None = None,
) -> Product | None:
    """Update product metadata. Returns None if not found."""
    product = get_product(db, product_id, organization_id)
    if not product:
        return None

    if name is not None:
        product.name = name.strip()
    if brand is not None:
        product.brand = brand.strip()
    if category is not None:
        product.category = category.strip()
    if barcode is not None:
        product.barcode = barcode.strip()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            f"A product with barcode '{barcode}' already exists in your organization."
        )

    db.refresh(product)
    return product


def update_product_status(
    db: Session,
    product_id: UUID,
    organization_id: UUID,
    new_status: str,
) -> Product | None:
    """Soft-activate/deactivate a product."""
    product = get_product(db, product_id, organization_id)
    if not product:
        return None

    product.status = ProductStatus(new_status)
    db.commit()
    db.refresh(product)
    return product
