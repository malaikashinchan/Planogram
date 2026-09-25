"""
Business logic for Users — with organization isolation.
"""

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.app.models import User, UserStatus, Role


def get_users(
    db: Session,
    organization_id: UUID,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
) -> list[User]:
    """List users within the organization."""
    query = select(User).where(User.organization_id == organization_id)

    if status_filter:
        query = query.where(User.status == UserStatus(status_filter))

    query = query.offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_user(
    db: Session,
    user_id: UUID,
    organization_id: UUID,
) -> User | None:
    """Get a single user by ID, scoped to the organization."""
    return db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )


def update_user_role(
    db: Session,
    user_id: UUID,
    organization_id: UUID,
    role_name: str,
) -> User | None:
    """
    Replace the user's roles with the specified single role.
    Returns None if user or role not found.
    """
    user = get_user(db, user_id, organization_id)
    if not user:
        return None

    role = db.scalar(select(Role).where(Role.name == role_name.upper()))
    if not role:
        raise ValueError(f"Role '{role_name}' does not exist.")

    user.roles.clear()
    user.roles.append(role)

    db.commit()
    db.refresh(user)
    return user


def update_user_status(
    db: Session,
    user_id: UUID,
    organization_id: UUID,
    new_status: str,
) -> User | None:
    """
    Soft-activate/deactivate a user.
    Returns None if user not found.
    """
    user = get_user(db, user_id, organization_id)
    if not user:
        return None

    user.status = UserStatus(new_status)

    db.commit()
    db.refresh(user)
    return user

def create_user(
    db: Session,
    organization_id: UUID,
    email: str,
    first_name: str,
    last_name: str,
    role_name: str
) -> User:
    from backend.app.core.security import hash_password
    import uuid
    import secrets
    
    normalized_email = email.lower().strip()
    
    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )
    if existing_user:
        raise ValueError("An account with this email already exists.")
        
    role = db.scalar(select(Role).where(Role.name == role_name.upper()))
    if not role:
        raise ValueError(f"Role '{role_name}' does not exist.")

    # Temporary password that the user must reset via forgot-password/invite flow
    temp_password = secrets.token_urlsafe(12)
    
    user = User(
        id=uuid.uuid4(),
        organization_id=organization_id,
        email=normalized_email,
        password_hash=hash_password(temp_password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        status=UserStatus.ACTIVE,
        email_verified_at=None,
    )
    user.roles.append(role)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
