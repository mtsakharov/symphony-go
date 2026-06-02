"""Media lifecycle domain exceptions."""

from __future__ import annotations

from app.media.schemas import VideoUploadFailureCode


class MediaAssetNotFoundError(Exception):
    """Raised when a media asset does not exist."""


class MediaLifecycleError(Exception):
    """Raised when a lifecycle transition is invalid."""


class VideoUploadValidationError(Exception):
    """Raised when a video upload request fails validation."""

    def __init__(self, code: VideoUploadFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class MediaStorageError(Exception):
    """Raised when media storage operations fail."""

