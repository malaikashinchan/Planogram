"""
FastAPI dependencies for authentication and authorization.

get_current_user  — checks Authorization: Bearer JWT first, then
                    falls back to the session_token cookie.
                    This prevents session collision when multiple
                    users share the same browser.

require_roles     — factory that returns a dependency enforcing
                    that the user has at least one of the
                    specified roles.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.auth.service import get_user_from_session
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models import User


SESSION_COOKIE_NAME = "session_token"


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Authentication resolution order:
    1. Authorization: Bearer <JWT>  — preferred (short-lived, user-specific)
    2. session_token cookie         — fallback (long-lived)

    By preferring the JWT, we ensure the frontend's explicit login always
    takes precedence over a stale cookie from a previously logged-in user
    on the same browser.
    """

    # ── 1. Try Bearer JWT ───────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_jwt = auth_header.removeprefix("Bearer ").strip()
        if raw_jwt:
            try:
                user_id = decode_access_token(raw_jwt)
                user = db.scalar(select(User).where(User.id == user_id))
                if user:
                    from backend.app.models.user import UserStatus
                    if user.status == UserStatus.ACTIVE:
                        return user
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Account is inactive.",
                    )
            except Exception:
                # JWT is invalid or expired — fall through to cookie
                pass

    # ── 2. Try session cookie ────────────────────────────────────────
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        try:
            return get_user_from_session(db, session_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )


def require_roles(*allowed_roles: str):
    """
    Returns a dependency that checks whether the current user
    has at least one of the allowed roles.

    Usage in a router:

        @router.get("/admin-only", dependencies=[Depends(require_roles("ADMIN"))])

    or as a parameter:

        current_user: User = Depends(require_roles("ADMIN", "MANAGER"))
    """

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> User:
        current_user = get_current_user(request, db)

        user_role_names = {role.name for role in current_user.roles}

        if not user_role_names.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return Depends(dependency)
