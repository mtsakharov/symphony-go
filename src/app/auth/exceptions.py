"""Auth domain exceptions."""


class AuthError(Exception):
    """Base authentication exception."""


class InvalidCredentialsError(AuthError):
    """Raised when credentials do not match a principal."""


class PrincipalInactiveError(AuthError):
    """Raised when a principal exists but is inactive."""


class InvalidTokenError(AuthError):
    """Raised when a bearer token cannot be decoded."""
