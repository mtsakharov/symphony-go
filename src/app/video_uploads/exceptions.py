"""Domain exceptions for video uploads."""

from app.video_uploads.schemas import VideoUploadFailureCode


class VideoUploadValidationError(Exception):
    """Raised when a requested upload violates validation constraints."""

    def __init__(self, code: VideoUploadFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code
