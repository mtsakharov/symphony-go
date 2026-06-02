"""Storage helpers for media lifecycle cleanup."""

from __future__ import annotations

from pathlib import Path

from app.media.exceptions import MediaStorageError


class MediaStorage:
    """Storage interface for lifecycle cleanup."""

    def delete(self, storage_path: str) -> None:
        """Delete the object at the given storage path."""

        raise NotImplementedError


class LocalMediaStorage(MediaStorage):
    """Filesystem-backed storage for media lifecycle cleanup."""

    def __init__(self, *, storage_dir: Path) -> None:
        self.storage_dir = storage_dir.resolve()

    def delete(self, storage_path: str) -> None:
        """Delete a stored file if present."""

        try:
            self.resolve_path(storage_path).unlink(missing_ok=True)
        except OSError as exc:
            raise MediaStorageError("Failed to delete stored media") from exc

    def resolve_path(self, storage_path: str) -> Path:
        """Resolve a storage path under the configured root."""

        candidate = (self.storage_dir / storage_path).resolve()
        if self.storage_dir != candidate and self.storage_dir not in candidate.parents:
            raise MediaStorageError("Resolved storage path escapes the configured media directory")
        return candidate

