
"""
Business logic for Products — with organization isolation.
"""

import io
import uuid
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Product, ProductStatus


# ============================================================
# File Import Configuration
# ============================================================

SUPPORTED_PRODUCT_EXTENSIONS = (
    ".csv",
    ".json",
    ".xls",
    ".xlsx",
)

REQUIRED_PRODUCT_COLUMNS = (
    "sku_code",
    "name",
)

OPTIONAL_PRODUCT_COLUMNS = (
    "brand",
    "category",
)


# ============================================================
# File Parsing Helpers
# ============================================================

def _read_product_file(upload_file) -> pd.DataFrame:
    """
    Read a product catalogue from CSV, JSON, XLS, or XLSX.

    File format is determined strictly from the file extension.
    """

    filename = (
        upload_file.filename.lower().strip()
        if upload_file.filename
        else ""
    )

    if not filename:
        raise ValueError(
            "Uploaded file must have a filename."
        )

    if not filename.endswith(SUPPORTED_PRODUCT_EXTENSIONS):
        raise ValueError(
            "Unsupported file format. "
            "Please upload CSV, JSON, XLS, or XLSX."
        )

    content = upload_file.file.read()

    if not content:
        raise ValueError(
            "The uploaded file is empty."
        )

    try:
        if filename.endswith(".json"):
            df = pd.read_json(
                io.BytesIO(content)
            )

        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(
                io.BytesIO(content)
            )

        elif filename.endswith(".csv"):
            df = pd.read_csv(
                io.BytesIO(content)
            )

        else:
            # Defensive check. The extension was already
            # validated above.
            raise ValueError(
                "Unsupported file format. "
                "Please upload CSV, JSON, XLS, or XLSX."
            )

    except ValueError:
        raise

    except Exception as exc:
        raise ValueError(
            f"Failed to parse file: {exc}"
        )

    if df.empty:
        raise ValueError(
            "The uploaded file contains no rows."
        )

    return df


def _map_product_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Map columns strictly by POSITION.

    Expected order:

        1. SKU
        2. Name
        3. Brand
        4. Category

    Column header names in the uploaded file are ignored.

    Any columns after the first four are ignored.
    """

    if len(df.columns) < 2:
        raise ValueError(
            "Product file must contain at least 2 columns "
            "(SKU and Name)."
        )

    df = df.copy()

    columns = list(df.columns)

    columns[0] = "sku_code"
    columns[1] = "name"

    if len(columns) > 2:
        columns[2] = "brand"

    if len(columns) > 3:
        columns[3] = "category"

    df.columns = columns

    return df


def _is_null(value) -> bool:
    """
    Safely determine whether a value is null.

    Handles:
        None
        NaN
        NaT
        pd.NA

    without causing ambiguous truth-value errors.
    """

    if value is None:
        return True

    try:
        result = pd.isna(value)

        if isinstance(result, bool):
            return result

        return False

    except (TypeError, ValueError):
        return False


def _clean_required_string(
    value,
    field_name: str,
) -> str:
    """
    Validate and normalize a required string field.
    """

    if _is_null(value):
        raise ValueError(
            f"{field_name} contains empty or null values."
        )

    value = str(value).strip()

    if not value:
        raise ValueError(
            f"{field_name} contains empty values."
        )

    return value


def _clean_optional_string(value):
    """
    Normalize an optional string field.

    Null-like values become Python None.
    """

    if _is_null(value):
        return None

    value = str(value).strip()

    return value if value else None


def _validate_product_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate and normalize the product catalogue.

    Required:
        sku_code
        name

    Optional:
        brand
        category
    """

    df = df.copy()

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    for column in REQUIRED_PRODUCT_COLUMNS:
        if column not in df.columns:
            raise ValueError(
                f"Required column '{column}' is missing."
            )

    # --------------------------------------------------------
    # Clean required fields
    # --------------------------------------------------------

    df["sku_code"] = df["sku_code"].apply(
        lambda value: _clean_required_string(
            value,
            "SKU",
        )
    )

    df["name"] = df["name"].apply(
        lambda value: _clean_required_string(
            value,
            "Name",
        )
    )

    # --------------------------------------------------------
    # Clean optional fields
    # --------------------------------------------------------

    if "brand" in df.columns:
        df["brand"] = df["brand"].apply(
            _clean_optional_string
        )

    if "category" in df.columns:
        df["category"] = df["category"].apply(
            _clean_optional_string
        )

    # --------------------------------------------------------
    # Duplicate SKU validation inside uploaded file
    # --------------------------------------------------------

    duplicate_mask = df["sku_code"].duplicated(
        keep=False
    )

    if duplicate_mask.any():
        duplicate_skus = sorted(
            df.loc[
                duplicate_mask,
                "sku_code",
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            "Duplicate SKU codes found in the uploaded file: "
            f"{duplicate_skus}"
        )

    return df


# ============================================================
# Product Queries
# ============================================================

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
            .where(
                Product.organization_id == organization_id
            )
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


# ============================================================
# Create Product
# ============================================================

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
        sku_code = (
            f"SKU_{str(uuid.uuid4())[:8].upper()}"
        )

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
                f"A product with SKU '{sku_code}' "
                "already exists in your organization."
            )

        elif "uq_organization_barcode" in error_msg:
            raise ValueError(
                f"A product with barcode '{barcode}' "
                "already exists in your organization."
            )

        raise ValueError(
            "A product with these details already exists."
        )

    db.refresh(product)

    return product


# ============================================================
# Update Product
# ============================================================

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

    product = get_product(
        db,
        product_id,
        organization_id,
    )

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
            f"A product with barcode '{barcode}' "
            "already exists in your organization."
        )

    db.refresh(product)

    return product


# ============================================================
# Update Product Status
# ============================================================

def update_product_status(
    db: Session,
    product_id: UUID,
    organization_id: UUID,
    new_status: str,
) -> Product | None:
    """Soft-activate/deactivate a product."""

    product = get_product(
        db,
        product_id,
        organization_id,
    )

    if not product:
        return None

    product.status = ProductStatus(new_status)

    db.commit()
    db.refresh(product)

    return product


# ============================================================
# Product Catalogue Import
# ============================================================

def ingest_product_catalogue(
    db: Session,
    organization_id: UUID,
    upload_file,
) -> dict:
    """
    Parse and bulk upsert a product catalogue.

    Supported formats:
        CSV
        JSON
        XLS
        XLSX

    Columns are mapped STRICTLY by position:

        1. SKU
        2. Name
        3. Brand
        4. Category

    Additional columns are ignored.

    Required fields:
        SKU
        Name

    Optional fields:
        Brand
        Category
    """

    # --------------------------------------------------------
    # Read
    # --------------------------------------------------------

    df = _read_product_file(
        upload_file
    )

    # --------------------------------------------------------
    # Positional mapping
    # --------------------------------------------------------

    df = _map_product_columns(
        df
    )

    # --------------------------------------------------------
    # Validation + normalization
    # --------------------------------------------------------

    df = _validate_product_dataframe(
        df
    )

    created = 0
    updated = 0

    # --------------------------------------------------------
    # Process rows
    # --------------------------------------------------------

    for row in df.to_dict(
        orient="records"
    ):

        sku = row["sku_code"]
        name = row["name"]

        brand = _clean_optional_string(
            row.get("brand")
        )

        category = _clean_optional_string(
            row.get("category")
        )

        # ----------------------------------------------------
        # Organization-scoped lookup
        # ----------------------------------------------------

        product = db.scalar(
            select(Product).where(
                Product.sku_code == sku,
                Product.organization_id
                == organization_id,
            )
        )

        # ----------------------------------------------------
        # Update existing product
        # ----------------------------------------------------

        if product:

            product.name = name
            product.brand = brand
            product.category = category

            updated += 1

        # ----------------------------------------------------
        # Create new product
        # ----------------------------------------------------

        else:

            new_product = Product(
                organization_id=organization_id,
                sku_code=sku,
                name=name,
                brand=brand,
                category=category,
                status=ProductStatus.ACTIVE,
            )

            db.add(new_product)

            created += 1

    # --------------------------------------------------------
    # Commit everything together
    # --------------------------------------------------------

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        error_msg = str(exc.orig)

        if "uq_organization_sku" in error_msg:
            raise ValueError(
                "A product with one of the uploaded SKU codes "
                "already exists in your organization."
            )

        if "uq_organization_barcode" in error_msg:
            raise ValueError(
                "A product with one of the uploaded barcodes "
                "already exists in your organization."
            )

        raise ValueError(
            "Failed to import products because of a "
            "database constraint violation."
        )

    return {
        "created": created,
        "updated": updated,
    }


# ============================================================
# Product Catalogue Preview
# ============================================================

def preview_product_catalogue(
    upload_file,
) -> dict:
    """
    Parse and preview the first five rows of a product
    catalogue.

    This function DOES NOT modify the database.

    Columns are mapped STRICTLY by position:

        1. SKU
        2. Name
        3. Brand
        4. Category

    Additional columns are ignored.

    Null values in optional fields are returned as JSON null.
    """

    # --------------------------------------------------------
    # Read
    # --------------------------------------------------------

    df = _read_product_file(
        upload_file
    )

    # --------------------------------------------------------
    # Positional mapping
    # --------------------------------------------------------

    df = _map_product_columns(
        df
    )

    # --------------------------------------------------------
    # Validation + normalization
    #
    # This is intentionally the same validation used by
    # the actual import, so preview does not show a file
    # that will later fail during upload.
    # --------------------------------------------------------

    df = _validate_product_dataframe(
        df
    )

    # --------------------------------------------------------
    # Only expose supported product columns
    # --------------------------------------------------------

    preview_columns = [
        "sku_code",
        "name",
    ]

    if "brand" in df.columns:
        preview_columns.append(
            "brand"
        )

    if "category" in df.columns:
        preview_columns.append(
            "category"
        )

    preview_df = (
        df[preview_columns]
        .head(5)
        .copy()
    )

    # --------------------------------------------------------
    # JSON null safety
    #
    # Convert:
    #     NaN
    #     NaT
    #     pd.NA
    #
    # to:
    #     None
    #
    # FastAPI then serializes None as JSON null.
    # --------------------------------------------------------

    preview_df = preview_df.astype(
        object
    )

    preview_df = preview_df.where(
        pd.notna(preview_df),
        None,
    )

    return {
        "totalRows": len(df),
        "preview": preview_df.to_dict(
            orient="records"
        ),
    }