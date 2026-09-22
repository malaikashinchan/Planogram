import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.schemas import RegisterRequest
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.models import (
    AuthSession,
    AuthToken,
    AuthTokenType,
    Organization,
    OrgStatus,
    Role,
    User,
    UserStatus,
)


EMAIL_VERIFICATION_EXPIRE_HOURS = 24
PASSWORD_RESET_EXPIRE_HOURS = 1
SESSION_EXPIRE_DAYS = 30


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
#  Registration
# ──────────────────────────────────────────────

def register_user(
    db: Session,
    data: RegisterRequest,
) -> tuple[User, str]:
    """
    Creates an Organization + User + ADMIN role assignment
    and returns (user, raw_verification_token).
    """

    normalized_email = data.email.lower().strip()

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if existing_user:
        raise ValueError("An account with this email already exists.")

    organization = Organization(
        id=uuid.uuid4(),
        name=data.organization_name.strip(),
        slug=f"{data.organization_name.strip().lower().replace(' ', '-')}-{secrets.token_hex(4)}",
        status=OrgStatus.ACTIVE,
    )

    # Derive names from email if not provided
    email_prefix = normalized_email.split("@")[0]
    first_name = (data.first_name.strip() if data.first_name else email_prefix.capitalize())
    last_name = (data.last_name.strip() if data.last_name else "User")

    user = User(
        id=uuid.uuid4(),
        organization=organization,
        email=normalized_email,
        password_hash=hash_password(data.password),
        first_name=first_name,
        last_name=last_name,
        status=UserStatus.ACTIVE,
        email_verified_at=None,
    )

    admin_role = db.scalar(
        select(Role).where(Role.name == "ADMIN")
    )

    if not admin_role:
        raise ValueError("ADMIN role does not exist. Run seed_roles.py first.")

    user.roles.append(admin_role)

    db.add(organization)
    db.add(user)
    db.flush()

    raw_token = _generate_token()

    verification_token = AuthToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        token_type=AuthTokenType.EMAIL_VERIFICATION,
        expires_at=_now() + timedelta(
            hours=EMAIL_VERIFICATION_EXPIRE_HOURS
        ),
    )

    db.add(verification_token)
    db.commit()
    db.refresh(user)

    return user, raw_token


# ──────────────────────────────────────────────
#  Email Verification
# ──────────────────────────────────────────────

def verify_email(db: Session, raw_token: str) -> User:
    """
    Validates the email-verification token and marks
    user.email_verified_at.
    """

    token_hash = _hash_token(raw_token)

    auth_token = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.token_type == AuthTokenType.EMAIL_VERIFICATION,
        )
    )

    if not auth_token:
        raise ValueError("Invalid verification token.")

    if auth_token.used_at is not None:
        raise ValueError("This verification token has already been used.")

    if auth_token.expires_at < _now():
        raise ValueError("This verification token has expired.")

    user = db.scalar(
        select(User).where(User.id == auth_token.user_id)
    )

    if not user:
        raise ValueError("User not found.")

    user.email_verified_at = _now()
    auth_token.used_at = _now()

    db.commit()
    db.refresh(user)

    return user


# ──────────────────────────────────────────────
#  Login (Authenticate + Create Session)
# ──────────────────────────────────────────────

def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Validates email + password. Returns the User if valid,
    raises ValueError otherwise.
    """

    normalized_email = email.lower().strip()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if not user:
        raise ValueError("Invalid email or password.")

    if user.status != UserStatus.ACTIVE:
        raise ValueError("This account has been deactivated.")

    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password.")

    return user


def create_session(db: Session, user: User) -> str:
    """
    Creates an auth_session row and returns the raw session token.
    The caller (router) will set this as an HTTP-only cookie.
    """

    raw_token = _generate_token()

    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=_now() + timedelta(days=SESSION_EXPIRE_DAYS),
    )

    user.last_login_at = _now()

    db.add(session)
    db.commit()

    return raw_token


def get_user_from_session(db: Session, raw_token: str) -> User:
    """
    Looks up an active (non-revoked, non-expired) session and
    returns the associated User.
    """

    token_hash = _hash_token(raw_token)

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash,
        )
    )

    if not session:
        raise ValueError("Invalid session.")

    if session.revoked_at is not None:
        raise ValueError("Session has been revoked.")

    if session.expires_at < _now():
        raise ValueError("Session has expired.")

    user = db.scalar(
        select(User).where(User.id == session.user_id)
    )

    if not user or user.status != UserStatus.ACTIVE:
        raise ValueError("User not found or inactive.")

    return user


# ──────────────────────────────────────────────
#  Logout (Revoke Session)
# ──────────────────────────────────────────────

def revoke_session(db: Session, raw_token: str) -> None:
    """Marks the session as revoked."""

    token_hash = _hash_token(raw_token)

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash,
        )
    )

    if session and session.revoked_at is None:
        session.revoked_at = _now()
        db.commit()


# ──────────────────────────────────────────────
#  Forgot Password (Create Reset Token)
# ──────────────────────────────────────────────

def create_password_reset_token(db: Session, email: str) -> str | None:
    """
    If the email exists, creates a PASSWORD_RESET token and
    returns the raw token. Returns None if user not found
    (to prevent email enumeration).
    """

    normalized_email = email.lower().strip()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if not user:
        return None

    raw_token = _generate_token()

    reset_token = AuthToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        token_type=AuthTokenType.PASSWORD_RESET,
        expires_at=_now() + timedelta(
            hours=PASSWORD_RESET_EXPIRE_HOURS
        ),
    )

    db.add(reset_token)
    db.commit()

    return raw_token


# ──────────────────────────────────────────────
#  Reset Password
# ──────────────────────────────────────────────

def reset_password(db: Session, raw_token: str, new_password: str) -> User:
    """
    Validates the reset token and updates the user's password.
    """

    token_hash = _hash_token(raw_token)

    auth_token = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.token_type == AuthTokenType.PASSWORD_RESET,
        )
    )

    if not auth_token:
        raise ValueError("Invalid reset token.")

    if auth_token.used_at is not None:
        raise ValueError("This reset token has already been used.")

    if auth_token.expires_at < _now():
        raise ValueError("This reset token has expired.")

    user = db.scalar(
        select(User).where(User.id == auth_token.user_id)
    )

    if not user:
        raise ValueError("User not found.")

    user.password_hash = hash_password(new_password)
    auth_token.used_at = _now()

    db.commit()
    db.refresh(user)

    return user