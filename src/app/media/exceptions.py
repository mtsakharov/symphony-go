"""Media domain exceptions."""


class MediaNotFoundError(Exception):
    """Raised when a media record cannot be found."""


class UnsupportedMediaTypeError(Exception):
    """Raised when an uploaded file MIME type is not allowed."""


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured limit."""


class InvalidMediaFilenameError(Exception):
    """Raised when an uploaded file has an invalid filename."""


class EmptyMediaFileError(Exception):
    """Raised when an uploaded file has no content."""


class MediaStorageError(Exception):
    """Raised when media storage operations fail."""

