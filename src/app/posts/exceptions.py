"""Domain exceptions for posts."""


class PostNotFoundError(Exception):
    """Raised when a post cannot be found."""


class PostAuthorNotFoundError(Exception):
    """Raised when a referenced author does not exist."""
