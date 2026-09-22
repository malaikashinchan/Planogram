"""
FastAPI dependencies for authentication and authorization.

get_current_user  — extracts the session cookie, validates it,
                    and returns the authenticated User.
require_roles     — factory that returns a dependency enforcing
                    that the user has at least one of the
                    specified roles.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.service import get_user_from_session
from backend.app.core.database import get_db
from backend.app.models import User


SESSION_COOKIE_NAME = "session_token"


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Reads the `session_token` HTTP-only cookie from the request,
    validates the session in the database, and returns the User.
    """

    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    try:
        user = get_user_from_session(db, session_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    return user


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
