"""Video processing pipeline contracts and implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from app.assets.models import VideoAsset


@dataclass(slots=True)
class VideoProcessingResult:
    """Structured output produced by the transcode pipeline."""

    playback_metadata: dict[str, object]
    poster_metadata: dict[str, object]
    thumbnail_metadata: dict[str, object]


class VideoProcessingFailure(Exception):
    """Raised when the transcode pipeline cannot produce a playable asset."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class VideoTranscodePipeline(Protocol):
    """Protocol for a transcode pipeline."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        """Produce playback and image metadata for an uploaded asset."""


class DeterministicVideoTranscodePipeline:
    """In-process pipeline used by the service until an external worker is wired in."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        """Build stable derived metadata for a valid uploaded video."""

        base_path = PurePosixPath(asset.source_key)
        stem = str(base_path.with_suffix(""))

        return VideoProcessingResult(
            playback_metadata={
                "playback_url": f"{stem}/master.m3u8",
                "content_type": "application/x-mpegURL",
                "duration_seconds": 0.0,
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
