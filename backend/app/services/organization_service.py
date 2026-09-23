"""
Business logic for Organizations.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Organization


def get_organization(db: Session, organization_id: UUID) -> Organization | None:
    """Get an organization by ID."""
    return db.scalar(
        select(Organization).where(Organization.id == organization_id)
    )


def update_organization(
    db: Session,
    organization_id: UUID,
    name: str,
) -> Organization | None:
    """Update organization name. Returns None if not found."""
    org = db.scalar(
        select(Organization).where(Organization.id == organization_id)
    )

    if not org:
        return None

    org.name = name.strip()
    db.commit()
    db.refresh(org)

    return org
