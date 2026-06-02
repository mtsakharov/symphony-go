"""Domain exceptions for video-post lifecycle flows."""

from __future__ import annotations

from app.posts.schemas import VideoUploadFailureCode


class PostError(Exception):
    """Base post-domain exception."""


class PostNotFoundError(PostError):
    """Raised when a post does not exist."""


class PostValidationError(PostError):
    """Raised when a post request fails domain validation."""


class VideoUploadNotFoundError(PostError):
    """Raised when an upload intent cannot be found."""


class VideoUploadValidationError(PostValidationError):
    """Raised when upload initiation fails server-side validation."""

    def __init__(self, code: VideoUploadFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code
