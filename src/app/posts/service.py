"""Service layer for posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.posts.exceptions import PostNotFoundError
from app.posts.models import Post, PostType, VideoProcessingStatus
from app.posts.repository import PostRepository
from app.posts.schemas import (
    FeedResponse,
    MediaAssetResponse,
    PostDetailResponse,
    PostResponse,
    VideoMediaResponse,
)


class PostService:
    """Business logic for feed and post detail responses."""

    def __init__(self, repository: PostRepository | None = None) -> None:
        self.repository = repository or PostRepository()

    def list_feed(self, session: Session, *, page: int, limit: int) -> FeedResponse:
        """Return a paginated feed response."""

        offset = (page - 1) * limit
        posts = self.repository.list_feed(session, offset=offset, limit=limit)
        total = self.repository.count_posts(session)
        return FeedResponse(
            items=[self.serialize_post(post) for post in posts],
            page=page,
            limit=limit,
            total=total,
        )

    def get_post(self, session: Session, post_id: UUID) -> PostDetailResponse:
        """Return a single post or raise if absent."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")
        return PostDetailResponse.model_validate(self.serialize_post(post))

    def serialize_post(self, post: Post) -> PostResponse:
        """Map a post model to the API response contract."""

        return PostResponse(
            id=post.id,
            post_type=post.post_type,
            body=post.body,
            video_media=self._serialize_video_media(post),
            created_at=post.created_at,
            updated_at=post.updated_at,
        )

    def _serialize_video_media(self, post: Post) -> VideoMediaResponse | None:
        """Map stored video metadata to a stable API payload."""

        if post.post_type is not PostType.VIDEO or post.video_status is None:
            return None

        is_playable = (
            post.video_status is VideoProcessingStatus.READY
            and post.video_playback_reference is not None
            and post.video_playback_reference != ""
        )
        return VideoMediaResponse(
            status=post.video_status,
            is_playable=is_playable,
            caption=post.video_caption,
            duration_seconds=post.video_duration_seconds,
            poster=self._serialize_media_asset(
                post.video_poster_url,
                post.video_poster_width,
                post.video_poster_height,
            ),
            thumbnail=self._serialize_media_asset(
                post.video_thumbnail_url,
                post.video_thumbnail_width,
                post.video_thumbnail_height,
            ),
            playback_reference=post.video_playback_reference if is_playable else None,
            failure_reason=(
                post.video_failure_reason
                if post.video_status is VideoProcessingStatus.FAILED
                else None
            ),
        )

    def _serialize_media_asset(
        self,
        url: str | None,
        width: int | None,
        height: int | None,
    ) -> MediaAssetResponse | None:
        """Return a media asset only when the derived metadata is complete."""

        if not url or width is None or height is None:
            return None
        return MediaAssetResponse(url=url, width=width, height=height)
