"""Domain errors for tag workflows."""


class TagNotFoundError(Exception):
    """Raised when a tag cannot be found."""


class TagConflictError(Exception):
    """Raised when a tag violates a uniqueness constraint."""
