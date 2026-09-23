"""
Business logic for Products — with organization isolation.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import io
import pandas as pd
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


def ingest_product_catalogue(
    db: Session,
    organization_id: UUID,
    upload_file,
) -> dict:
    """
    Parse a CSV file and bulk upsert products.
    """
    content = upload_file.file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")

    # Validate columns
    required_cols = {"sku_id", "product_name", "brand", "category"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    created = 0
    updated = 0

    for _, row in df.iterrows():
        sku = str(row["sku_id"]).strip()
        name = str(row["product_name"]).strip()
        brand = str(row["brand"]).strip()
        category = str(row["category"]).strip()
        
        product = db.scalar(
            select(Product).where(
                Product.sku_code == sku,
                Product.organization_id == organization_id,
            )
        )

        if product:
            product.name = name
            product.brand = brand
            product.category = category
            updated += 1
        else:
            new_prod = Product(
                organization_id=organization_id,
                sku_code=sku,
                name=name,
                brand=brand,
                category=category,
                status=ProductStatus.ACTIVE,
            )
            db.add(new_prod)
            created += 1

    db.commit()
    return {"created": created, "updated": updated}
