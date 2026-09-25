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
    sku_code: str | None,
    name: str,
    brand: str | None = None,
    category: str | None = None,
    barcode: str | None = None,
) -> Product:
    """Create a new product. Raises ValueError on duplicate SKU or barcode."""
    if not sku_code:
        import uuid
        sku_code = f"SKU_{str(uuid.uuid4())[:8].upper()}"

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
    Parse a CSV, XLS, XLSX, or JSON file and bulk upsert products.
    Dynamically maps columns to standard names.
    """
    filename = upload_file.filename.lower() if upload_file.filename else ""
    content = upload_file.file.read()
    
    try:
        if filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Failed to parse file: {e}")

    # Check minimum columns
    if len(df.columns) < 2:
        raise ValueError("File must contain at least 2 columns (SKU and Name).")

    # Positional Mapping (Index-based)
    new_cols = list(df.columns)
    new_cols[0] = "sku_code"
    new_cols[1] = "name"
    if len(new_cols) > 2:
        new_cols[2] = "brand"
    if len(new_cols) > 3:
        new_cols[3] = "category"
        
    df.columns = new_cols

    created = 0
    updated = 0

    for _, row in df.iterrows():
        sku = str(row["sku_code"]).strip()
        name = str(row["name"]).strip()
        brand = str(row.get("brand", "")).strip() if "brand" in row and pd.notna(row["brand"]) else None
        category = str(row.get("category", "")).strip() if "category" in row and pd.notna(row["category"]) else None
        
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


def preview_product_catalogue(upload_file) -> dict:
    """
    Parse a file and return the first 5 rows with mapped column names.
    """
    filename = upload_file.filename.lower() if upload_file.filename else ""
    content = upload_file.file.read()
    
    try:
        if filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Failed to parse file: {e}")

    if len(df.columns) < 2:
        raise ValueError("File must contain at least 2 columns (SKU and Name).")

    new_cols = list(df.columns)
    new_cols[0] = "sku_code"
    new_cols[1] = "name"
    if len(new_cols) > 2:
        new_cols[2] = "brand"
    if len(new_cols) > 3:
        new_cols[3] = "category"
        
    df.columns = new_cols

    # Convert first 5 rows to dict and ensure NaN becomes None
    preview_df = df.head(5).replace({pd.NA: None, float('nan'): None})
    return {
        "totalRows": len(df),
        "preview": preview_df.to_dict('records')
    }
