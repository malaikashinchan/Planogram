"""
Authentication endpoints.

POST /register        — Create organization + user + verification token
POST /verify-email    — Validate email-verification token
POST /login           — Authenticate and set session cookie
GET  /me              — Return current authenticated user
POST /logout          — Revoke the session cookie
POST /forgot-password — Create a password-reset token
POST /reset-password  — Validate reset token and update password
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.email import (
    send_password_reset_email,
    send_verification_email,
)
from backend.app.auth.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from backend.app.auth.service import (
    authenticate_user,
    create_password_reset_token,
    create_session,
    register_user,
    reset_password,
    revoke_session,
    verify_email,
)
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token
from backend.app.models import User


router = APIRouter(prefix="/auth", tags=["Authentication"])


SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _set_session_cookie(response: Response, token: str) -> None:
    """Sets the session token as an HTTP-only, secure cookie."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,       # Set True in production (HTTPS)
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Deletes the session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def _build_user_response(user: User) -> UserResponse:
    """Converts a SQLAlchemy User into a Pydantic UserResponse."""
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        organization_id=user.organization_id,
        email_verified=user.email_verified_at is not None,
        roles=[role.name for role in user.roles],
    )


# ──────────────────────────────────────────────
#  POST /register
# ──────────────────────────────────────────────

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        user, raw_token = register_user(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    send_verification_email(user.email, raw_token)

    return MessageResponse(
        message="Registration successful. Please check your email to verify your account.",
    )


# ──────────────────────────────────────────────
#  POST /verify-email
# ──────────────────────────────────────────────

@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email_endpoint(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    try:
        verify_email(db, data.token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return MessageResponse(message="Email verified successfully.")


# ──────────────────────────────────────────────
#  POST /login
# ──────────────────────────────────────────────

@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        user = authenticate_user(db, data.email, data.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    raw_session_token = create_session(db, user)
    _set_session_cookie(response, raw_session_token)

    access_token = create_access_token(subject=str(user.id))

    return AuthResponse(
        access_token=access_token,
        user=_build_user_response(user),
    )


# ──────────────────────────────────────────────
#  GET /me
# ──────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return _build_user_response(current_user)


# ──────────────────────────────────────────────
#  POST /logout
# ──────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if session_token:
        revoke_session(db, session_token)

    _clear_session_cookie(response)

    return MessageResponse(message="Logged out successfully.")


# ──────────────────────────────────────────────
#  POST /forgot-password
# ──────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    raw_token = create_password_reset_token(db, data.email)

    if raw_token:
        send_password_reset_email(data.email, raw_token)

    # Always return the same message to prevent email enumeration
    return MessageResponse(
        message="If that email exists, a password reset link has been sent.",
    )


# ──────────────────────────────────────────────
#  POST /reset-password
# ──────────────────────────────────────────────

@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password_endpoint(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        reset_password(db, data.token, data.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return MessageResponse(message="Password reset successfully. You can now log in.")
