"""
Custom exceptions for the Planogram Compliance API.

These are raised by the service layer and caught/translated
by the FastAPI router layer into appropriate HTTP responses.
"""


class DuplicateEmailError(Exception):
    """Raised when a registration email already exists."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when email/password combination is wrong."""
    pass


class InvalidTokenError(Exception):
    """Raised when a verification/reset/session token is invalid, used, or expired."""
    pass


class InactiveAccountError(Exception):
    """Raised when a deactivated user tries to authenticate."""
    pass


class PermissionDeniedError(Exception):
    """Raised when a user lacks the required role."""
    pass


class OrganizationAccessError(Exception):
    """Raised when a user tries to access another organization's data."""
    pass


class NotFoundError(Exception):
    """Raised when a requested resource does not exist (within the user's org scope)."""
    pass
