"""Storage abstractions for uploaded media files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.media.exceptions import (
    EmptyMediaFileError,
    FileTooLargeError,
    InvalidMediaFilenameError,
    MediaStorageError,
)

_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True)
class StoredMedia:
    """Stored media file details."""

    filename: str
    storage_path: str
    size: int
    url: str | None


class MediaStorage:
    """Storage interface for uploaded media files."""

    async def save(
        self,
        upload_file: UploadFile,
        *,
        media_id: UUID,
        max_size_bytes: int,
    ) -> StoredMedia:
        """Persist an uploaded file and return its storage metadata."""

        raise NotImplementedError

    async def delete(self, storage_path: str) -> None:
        """Delete a stored file."""

        raise NotImplementedError

    def get_url(self, storage_path: str) -> str | None:
        """Resolve a public or internal URL for a stored file."""

        raise NotImplementedError


class LocalMediaStorage(MediaStorage):
    """Store uploaded media on the local filesystem."""

    def __init__(self, *, storage_dir: Path, public_url_prefix: str | None = None) -> None:
        self.storage_dir = storage_dir.resolve()
        self.public_url_prefix = public_url_prefix.rstrip("/") if public_url_prefix else None

    async def save(
        self,
        upload_file: UploadFile,
        *,
        media_id: UUID,
        max_size_bytes: int,
    ) -> StoredMedia:
        """Persist an uploaded file in local storage."""

        destination: Path | None = None
        size = 0
        try:
            sanitized_filename = sanitize_filename(upload_file.filename)
            extension = "".join(Path(sanitized_filename).suffixes).lower()
            relative_path = Path(media_id.hex[:2]) / f"{media_id.hex}{extension}"
            destination = self._resolve_storage_path(relative_path.as_posix())
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as output_file:
                while chunk := await upload_file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_size_bytes:
                        raise FileTooLargeError(
                            f"File exceeds the maximum allowed size of {max_size_bytes} bytes"
                        )
                    output_file.write(chunk)
        except Exception as exc:
            if destination is not None:
                destination.unlink(missing_ok=True)
            if isinstance(exc, (FileTooLargeError, InvalidMediaFilenameError)):
                raise
            raise MediaStorageError("Failed to store uploaded file") from exc
        finally:
            await upload_file.close()

        if size == 0:
            destination.unlink(missing_ok=True)
            raise EmptyMediaFileError("Uploaded file is empty")

        storage_path = relative_path.as_posix()
        return StoredMedia(
            filename=sanitized_filename,
            storage_path=storage_path,
            size=size,
            url=self.get_url(storage_path),
        )

    async def delete(self, storage_path: str) -> None:
        """Delete a locally stored file if it exists."""

        try:
            self._resolve_storage_path(storage_path).unlink(missing_ok=True)
        except OSError as exc:
            raise MediaStorageError("Failed to delete stored file") from exc

    def get_url(self, storage_path: str) -> str | None:
        """Return a static file URL for a stored file if configured."""

        if self.public_url_prefix is None:
            return None
        return f"{self.public_url_prefix}/{storage_path.lstrip('/')}"

    def _resolve_storage_path(self, storage_path: str) -> Path:
        """Resolve a relative storage path under the configured media directory."""

        candidate = (self.storage_dir / storage_path).resolve()
        if self.storage_dir != candidate and self.storage_dir not in candidate.parents:
            raise MediaStorageError("Resolved storage path escapes the configured media directory")
        return candidate


def sanitize_filename(filename: str | None) -> str:
    """Return a filesystem-safe filename preserving the original extension when possible."""

    if filename is None:
        raise InvalidMediaFilenameError("Uploaded file must include a filename")

    basename = Path(filename).name.strip()
    if basename in {"", ".", ".."}:
        raise InvalidMediaFilenameError("Uploaded file must include a valid filename")

    sanitized = _FILENAME_SAFE_PATTERN.sub("_", basename).strip("._")
    if not sanitized:
        raise InvalidMediaFilenameError("Uploaded file must include a valid filename")

    suffix = "".join(Path(sanitized).suffixes)
    if suffix and len(sanitized) > 255:
        stem = sanitized[: 255 - len(suffix)].rstrip("._")
        sanitized = f"{stem or 'upload'}{suffix}"
    else:
        sanitized = sanitized[:255]

    return sanitized or "upload"
