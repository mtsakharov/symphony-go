"""Posts domain exceptions."""


class PostNotFoundError(Exception):
    """Raised when a post does not exist or is not visible."""


class PostValidationError(Exception):
    """Raised when a post payload cannot be persisted."""

