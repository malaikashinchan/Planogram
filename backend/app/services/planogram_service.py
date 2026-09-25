"""
Business logic for Planograms — with organization isolation.

Enforces:
- Planogram belongs to organization
- Store belongs to organization (if provided)
- All product_ids in positions belong to organization
- No duplicate (shelf_id, position) within a version
- Published versions are immutable
- Version numbers auto-increment
"""

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    Planogram,
    PlanogramPosition,
    PlanogramStatus,
    PlanogramVersion,
    PlanogramVersionStatus,
    Product,
    Store,
)


def get_planograms(
    db: Session,
    organization_id: UUID,
    skip: int = 0,
    limit: int = 50,
    store_id: UUID | None = None,
) -> list[Planogram]:
    """List planograms within the organization."""
    query = select(Planogram).where(Planogram.organization_id == organization_id)
    if store_id:
        query = query.where(Planogram.store_id == store_id)
        
    return list(
        db.scalars(
            query.offset(skip).limit(limit)
        ).all()
    )


def get_planogram(
    db: Session,
    planogram_id: UUID,
    organization_id: UUID,
) -> Planogram | None:
    """Get a single planogram, scoped to organization."""
    return db.scalar(
        select(Planogram).where(
            Planogram.id == planogram_id,
            Planogram.organization_id == organization_id,
        )
    )


def delete_planogram(
    db: Session,
    planogram_id: UUID,
    organization_id: UUID,
) -> None:
    """Delete a planogram and all its versions."""
    planogram = get_planogram(db, planogram_id, organization_id)
    if not planogram:
        raise ValueError("Planogram not found.")
    
    # Must delete versions manually due to RESTRICT foreign key constraint
    db.query(PlanogramVersion).filter(PlanogramVersion.planogram_id == planogram_id).delete()
    
    db.delete(planogram)
    db.commit()


def create_planogram(
    db: Session,
    organization_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    store_id: UUID | None = None,
) -> Planogram:
    """
    Create a new root planogram.
    Validates store belongs to the organization if provided.
    """
    if store_id:
        store = db.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.organization_id == organization_id,
            )
        )
        if not store:
            raise ValueError("Store not found in your organization.")

    planogram = Planogram(
        organization_id=organization_id,
        store_id=store_id,
        code=code.strip(),
        name=name.strip(),
        status=PlanogramStatus.ACTIVE,
        created_by=user_id,
    )

    db.add(planogram)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            f"A planogram with code '{code}' already exists in your organization."
        )

    db.refresh(planogram)
    return planogram


# ── Versions ──


def get_versions(
    db: Session,
    planogram_id: UUID,
    organization_id: UUID,
) -> list[PlanogramVersion]:
    """List all versions of a planogram (after verifying org ownership)."""
    planogram = get_planogram(db, planogram_id, organization_id)
    if not planogram:
        return []

    return list(
        db.scalars(
            select(PlanogramVersion)
            .where(PlanogramVersion.planogram_id == planogram_id)
            .order_by(PlanogramVersion.version_number)
        ).all()
    )


def get_version(
    db: Session,
    planogram_id: UUID,
    version_id: UUID,
    organization_id: UUID,
) -> PlanogramVersion | None:
    """Get a specific version, with org ownership check on the parent planogram."""
    planogram = get_planogram(db, planogram_id, organization_id)
    if not planogram:
        return None

    return db.scalar(
        select(PlanogramVersion).where(
            PlanogramVersion.id == version_id,
            PlanogramVersion.planogram_id == planogram_id,
        )
    )


def get_positions_for_version(
    db: Session,
    version_id: UUID,
) -> list[PlanogramPosition]:
    """Get all positions for a version."""
    return list(
        db.scalars(
            select(PlanogramPosition)
            .where(PlanogramPosition.planogram_version_id == version_id)
            .order_by(PlanogramPosition.shelf_id, PlanogramPosition.position)
        ).all()
    )


def create_version(
    db: Session,
    planogram_id: UUID,
    organization_id: UUID,
    user_id: UUID,
    positions: list[dict],
) -> PlanogramVersion:
    """
    Create a new version with positions.
    
    Validates:
    - Planogram belongs to org
    - All product_ids belong to org
    - No duplicate (shelf_id, position) pairs
    - Auto-increments version_number
    
    Single transaction.
    """
    planogram = get_planogram(db, planogram_id, organization_id)
    if not planogram:
        raise ValueError("Planogram not found.")

    # ── Validate no duplicate shelf positions ──
    seen_positions = set()
    for pos in positions:
        key = (pos["shelf_id"], pos["position"])
        if key in seen_positions:
            raise ValueError(
                f"Duplicate position: shelf {pos['shelf_id']}, position {pos['position']}."
            )
        seen_positions.add(key)

    # ── Validate all products belong to this organization ──
    product_ids = {pos["product_id"] for pos in positions}
    existing_products = set(
        db.scalars(
            select(Product.id).where(
                Product.id.in_(product_ids),
                Product.organization_id == organization_id,
            )
        ).all()
    )

    missing = product_ids - existing_products
    if missing:
        raise ValueError(
            f"Products not found in your organization: {[str(m) for m in missing]}"
        )

    # ── Auto-increment version number ──
    max_version = db.scalar(
        select(func.max(PlanogramVersion.version_number)).where(
            PlanogramVersion.planogram_id == planogram_id
        )
    )
    next_version = (max_version or 0) + 1

    # ── Create version + positions in one transaction ──
    version = PlanogramVersion(
        planogram_id=planogram_id,
        version_number=next_version,
        status=PlanogramVersionStatus.DRAFT,
        created_by=user_id,
    )

    db.add(version)
    db.flush()  # Get version.id for positions

    for pos in positions:
        db.add(PlanogramPosition(
            planogram_version_id=version.id,
            product_id=pos["product_id"],
            shelf_id=pos["shelf_id"],
            position=pos["position"],
        ))

    db.commit()
    db.refresh(version)

    return version


def ingest_planogram(
    db: Session,
    organization_id: UUID,
    user_id: UUID,
    upload_file,
    store_uuid: UUID | None = None,
    name: str | None = None,
) -> PlanogramVersion:
    from backend.app.utils.planogram_parser import PlanogramParser
    from backend.app.utils.planogram_validator import PlanogramValidator

    # 1. Parse and validate canonical data
    canonical_data = PlanogramParser.parse_upload(upload_file)
    PlanogramValidator.validate_canonical(canonical_data)

    code = canonical_data["planogram_code"]
    store_code = canonical_data.get("store_id")

    # 2. Resolve store UUID if provided as a string code (e.g. "STORE_001") and not explicitly passed
    if not store_uuid and store_code:
        store = db.scalar(
            select(Store).where(Store.code == store_code, Store.organization_id == organization_id)
        )
        if not store:
            raise ValueError(f"Store code '{store_code}' not found in organization.")
        store_uuid = store.id

    # 3. Find or Create Planogram
    planogram = db.scalar(
        select(Planogram).where(Planogram.code == code, Planogram.organization_id == organization_id)
    )
    if not planogram:
        planogram_name = name if name and name.strip() else f"Planogram {code}"
        planogram = create_planogram(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            code=code,
            name=planogram_name,
            store_id=store_uuid,
        )

    # 4. Resolve SKU codes to Product UUIDs and build positions list
    # Collect all unique SKU string codes from the upload
    uploaded_skus = set()
    for shelf in canonical_data["shelves"]:
        for product in shelf["products"]:
            uploaded_skus.add(product["sku_id"])

    # Fetch mapping of sku -> product.id
    db_products = list(
        db.scalars(
            select(Product).where(
                Product.sku_code.in_(uploaded_skus),
                Product.organization_id == organization_id,
            )
        ).all()
    )
    sku_to_uuid = {p.sku_code: p.id for p in db_products}

    # Verify all SKUs exist
    missing_skus = uploaded_skus - set(sku_to_uuid.keys())
    if missing_skus:
        raise ValueError(f"Products not found in your organization: {sorted(list(missing_skus))}")

    # Build the flat list of position dicts expected by create_version
    positions = []
    for shelf in canonical_data["shelves"]:
        for product in shelf["products"]:
            positions.append({
                "shelf_id": shelf["shelf_id"],
                "position": product["position"],
                "product_id": sku_to_uuid[product["sku_id"]],
            })

    # 5. Create version and positions using the existing validated method
    version = create_version(
        db=db,
        planogram_id=planogram.id,
        organization_id=organization_id,
        user_id=user_id,
        positions=positions,
    )

    # 6. Mark as PUBLISHED instantly (simplified workflow)
    version.status = PlanogramVersionStatus.PUBLISHED
    db.commit()
    db.refresh(version)

    return version
