"""
Business logic for Stores — with organization isolation.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Store, StoreStatus


def get_stores(
    db: Session,
    organization_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Store]:
    """List stores within the organization."""
    return list(
        db.scalars(
            select(Store)
            .where(Store.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        ).all()
    )


def get_store(
    db: Session,
    store_id: UUID,
    organization_id: UUID,
) -> Store | None:
    """Get a single store, scoped to organization."""
    return db.scalar(
        select(Store).where(
            Store.id == store_id,
            Store.organization_id == organization_id,
        )
    )


def create_store(
    db: Session,
    organization_id: UUID,
    code: str,
    name: str,
    address: str | None = None,
) -> Store:
    """Create a new store. Raises ValueError on duplicate code."""
    store = Store(
        organization_id=organization_id,
        code=code.strip(),
        name=name.strip(),
        address=address.strip() if address else None,
        status=StoreStatus.ACTIVE,
    )

    db.add(store)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            f"A store with code '{code}' already exists in your organization."
        )

    db.refresh(store)
    return store


def update_store(
    db: Session,
    store_id: UUID,
    organization_id: UUID,
    name: str | None = None,
    address: str | None = None,
) -> Store | None:
    """Update store metadata. Returns None if not found."""
    store = get_store(db, store_id, organization_id)
    if not store:
        return None

    if name is not None:
        store.name = name.strip()
    if address is not None:
        store.address = address.strip()

    db.commit()
    db.refresh(store)
    return store


def update_store_status(
    db: Session,
    store_id: UUID,
    organization_id: UUID,
    new_status: str,
) -> Store | None:
    """Soft-activate/deactivate a store."""
    store = get_store(db, store_id, organization_id)
    if not store:
        return None

    store.status = StoreStatus(new_status)
    db.commit()
    db.refresh(store)
    return store
