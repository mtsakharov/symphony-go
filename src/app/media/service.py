"""Service layer for media management."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.media.exceptions import MediaNotFoundError, MediaStorageError, UnsupportedMediaTypeError
from app.media.models import Media
from app.media.repository import MediaRepository
from app.media.schemas import MediaListResponse, MediaResponse
from app.media.storage import MediaStorage


class MediaService:
    """Business logic for media upload and metadata management."""

    def __init__(
        self,
        *,
        settings: Settings,
        storage: MediaStorage,
        repository: MediaRepository | None = None,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.repository = repository or MediaRepository()

    async def create_media(self, session: Session, upload_file: UploadFile) -> MediaResponse:
        """Store a media file and persist its metadata."""

        content_type = upload_file.content_type or ""
        if content_type not in self.settings.media_allowed_content_types:
            raise UnsupportedMediaTypeError("Unsupported media type")

        media_id = uuid4()
        stored_file = await self.storage.save(
            upload_file,
            media_id=media_id,
            max_size_bytes=self.settings.media_max_size_bytes,
        )

        media = Media(
            id=media_id,
            filename=stored_file.filename,
            content_type=content_type,
            size=stored_file.size,
            storage_path=stored_file.storage_path,
        )

        try:
            self.repository.create(session, media=media)
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            await self.storage.delete(stored_file.storage_path)
            raise MediaStorageError("Failed to persist media metadata") from exc

        session.refresh(media)
        return self._to_response(media)

    def list_media(self, session: Session, *, page: int, limit: int) -> MediaListResponse:
        """Return a paginated list of uploaded media."""

        offset = (page - 1) * limit
        items = self.repository.list_media(session, offset=offset, limit=limit)
        total = self.repository.count_media(session)
        return MediaListResponse(
            items=[self._to_response(media) for media in items],
            page=page,
            limit=limit,
            total=total,
        )

    def get_media(self, session: Session, media_id: UUID) -> MediaResponse:
        """Return media metadata by id."""

        media = self.repository.get_by_id(session, media_id)
        if media is None:
            raise MediaNotFoundError("Media not found")
        return self._to_response(media)

    async def delete_media(self, session: Session, media_id: UUID) -> None:
        """Delete media metadata and the stored file."""

        media = self.repository.get_by_id(session, media_id)
        if media is None:
            raise MediaNotFoundError("Media not found")

        await self.storage.delete(media.storage_path)
        try:
            self.repository.delete(session, media=media)
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise MediaStorageError("Failed to delete media metadata") from exc

    def _to_response(self, media: Media) -> MediaResponse:
        """Serialize a media entity with its resolved URL."""

        return MediaResponse.from_model(media, url=self.storage.get_url(media.storage_path))
