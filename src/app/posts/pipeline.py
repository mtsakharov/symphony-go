"""Processing pipeline contracts for video-post assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from app.posts.models import VideoAsset


@dataclass(slots=True)
class VideoProcessingResult:
    """Structured data emitted after a successful transcode."""

    playback_metadata: dict[str, object]
    poster_metadata: dict[str, object]
    thumbnail_metadata: dict[str, object]


class VideoProcessingFailure(Exception):
    """Raised when the video cannot be made playable."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class VideoProcessingPending(Exception):
    """Raised when processing is intentionally deferred."""


class VideoTranscodePipeline(Protocol):
    """Protocol for the pluggable transcode pipeline."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        """Produce playback metadata for a stored asset."""


class DeterministicVideoTranscodePipeline:
    """In-process pipeline used for development and deterministic tests."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        """Build stable derived playback metadata from the upload source key."""

        base_path = PurePosixPath(asset.source_key)
        stem = str(base_path.with_suffix(""))

        return VideoProcessingResult(
            playback_metadata={
                "playback_url": f"{stem}/master.m3u8",
                "content_type": "application/x-mpegURL",
                "duration_seconds": float(asset.upload.duration_seconds),
                "width": 1920,
                "height": 1080,
            },
            poster_metadata={
                "url": f"{stem}/poster.jpg",
                "content_type": "image/jpeg",
                "width": 1920,
                "height": 1080,
            },
            thumbnail_metadata={
                "url": f"{stem}/thumbnail.jpg",
                "content_type": "image/jpeg",
                "width": 480,
                "height": 270,
            },
        )
