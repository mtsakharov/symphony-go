"""Posts domain exceptions."""


class PostValidationError(Exception):
    """Raised when a post creation request is invalid."""


class MediaAssetNotFoundError(PostValidationError):
    """Raised when a referenced media asset does not exist."""


class DuplicateAssetReferenceError(PostValidationError):
    """Raised when a request references the same asset more than once."""

