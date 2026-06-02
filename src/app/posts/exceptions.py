"""Posts domain exceptions."""


class PostNotFoundError(Exception):
    """Raised when a post cannot be found."""


class PostAuthorNotFoundError(Exception):
    """Raised when a post author cannot be found."""


class PostIndexSyncError(Exception):
    """Raised when post index synchronization fails."""
