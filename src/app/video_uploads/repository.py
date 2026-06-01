"""Persistence helpers for video upload intents."""

from sqlalchemy.orm import Session

from app.video_uploads.models import VideoUpload


class VideoUploadRepository:
    """Data access helpers for video uploads."""

    def create(self, session: Session, *, upload: VideoUpload) -> None:
        """Persist a new upload intent."""

        session.add(upload)
