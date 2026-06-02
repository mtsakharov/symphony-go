"""Service layer for the video-post lifecycle."""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.posts.exceptions import (
    PostNotFoundError,
    PostValidationError,
    VideoUploadNotFoundError,
    VideoUploadValidationError,
)
from app.posts.models import Post, PostStatus, PostType, VideoAsset, VideoAssetStatus, VideoUpload
from app.posts.pipeline import (
    VideoProcessingFailure,
    VideoProcessingPending,
    VideoProcessingResult,
    VideoTranscodePipeline,
)
from app.posts.repository import PostRepository
from app.posts.schemas import (
    PostCreate,
    PostListResponse,
    PostResponse,
    VideoAssetInput,
    VideoAssetResponse,
    VideoUploadAssetResponse,
    VideoUploadCompleteRequest,
    VideoUploadCreateRequest,
    VideoUploadFailureCode,
    VideoUploadResponse,
)
from app.users.exceptions import UserNotFoundError
from app.users.repository import UserRepository


class VideoAssetProcessor:
    """Drive processing transitions for a post's current video asset."""

    def __init__(
        self,
        *,
        repository: PostRepository,
        pipeline: VideoTranscodePipeline,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.session_factory = session_factory

    def process_post_video(self, post_id: UUID) -> None:
        """Move the current asset to ready, failed, or leave it processing."""

        with self.session_factory() as session:
            post = self.repository.get_post_by_id(session, post_id)
            if post is None or post.video_asset is None:
                return

            asset = post.video_asset
            try:
                result = self.pipeline.transcode(asset)
            except VideoProcessingPending:
                return
            except VideoProcessingFailure as exc:
                self._mark_failed(post, asset, reason=exc.reason)
            else:
                self._mark_ready(post, asset, result=result)

            session.add(post)
            session.add(asset)
            session.commit()

    def _mark_ready(
        self,
        post: Post,
        asset: VideoAsset,
        *,
        result: VideoProcessingResult,
    ) -> None:
        """Persist a successful playable state."""

        post.status = PostStatus.READY
        asset.status = VideoAssetStatus.READY
        asset.is_playable = True
        asset.playback_metadata = result.playback_metadata
        asset.poster_metadata = result.poster_metadata
        asset.thumbnail_metadata = result.thumbnail_metadata
        asset.failure_reason = None

    def _mark_failed(self, post: Post, asset: VideoAsset, *, reason: str) -> None:
        """Persist an unplayable failed state."""

        post.status = PostStatus.FAILED
        asset.status = VideoAssetStatus.FAILED
        asset.is_playable = False
        asset.playback_metadata = None
        asset.poster_metadata = None
        asset.thumbnail_metadata = None
        asset.failure_reason = reason


class PostService:
    """Business logic for post lifecycle flows."""

    def __init__(
        self,
        *,
        repository: PostRepository | None = None,
        user_repository: UserRepository | None = None,
        settings: Settings | None = None,
        processor: VideoAssetProcessor,
    ) -> None:
        self.repository = repository or PostRepository()
        self.user_repository = user_repository or UserRepository()
        self.settings = settings or get_settings()
        self.processor = processor

    def create_post(self, session: Session, payload: PostCreate) -> PostResponse:
        """Create a post shell that can later receive a video upload."""

        if self.user_repository.get_by_id(session, payload.user_id) is None:
            raise UserNotFoundError("User not found")

        caption = payload.caption or ""
        if payload.post_type is PostType.TEXT and not caption:
            raise PostValidationError("Text posts require caption text")

        status = PostStatus.READY if payload.post_type is PostType.TEXT else PostStatus.DRAFT
        post = Post(
            user_id=payload.user_id,
            post_type=payload.post_type,
            caption=caption,
            status=status,
        )
        self.repository.create_post(session, post=post)
        session.commit()
        loaded_post = self.repository.get_post_by_id(session, post.id)
        if loaded_post is None:
            raise PostValidationError("Created post could not be loaded")
        return self._serialize_post(loaded_post)

    def initiate_video_upload(
        self,
        session: Session,
        *,
        post_id: UUID,
        payload: VideoUploadCreateRequest,
    ) -> VideoUploadResponse:
        """Reserve a validated upload slot for a video post."""

        post = self._get_required_video_post(session, post_id)
        if post.status not in {PostStatus.DRAFT, PostStatus.FAILED}:
            raise PostValidationError("Video upload can only be started from draft or failed posts")

        if len(payload.assets) != 1:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.INVALID_ASSET_COUNT,
                "Exactly one video asset is required",
            )

        asset = payload.assets[0]
        self._validate_upload_asset(asset)

        upload = VideoUpload(
            post=post,
            filename=asset.filename,
            mime_type=asset.mime_type,
            video_codec=asset.video_codec,
            audio_codec=asset.audio_codec,
            file_size_bytes=asset.file_size_bytes,
            duration_seconds=asset.duration_seconds,
            upload_path=self._build_upload_path(post.id, asset.filename),
        )
        post.status = PostStatus.UPLOADING
        self.repository.create_upload(session, upload=upload)
        session.commit()
        session.refresh(upload)

        return VideoUploadResponse(
            id=upload.id,
            status=upload.status,
            upload_path=upload.upload_path,
            created_at=upload.created_at,
            asset=VideoUploadAssetResponse(
                filename=upload.filename,
                mime_type=upload.mime_type,
                video_codec=upload.video_codec,
                audio_codec=upload.audio_codec,
                file_size_bytes=upload.file_size_bytes,
                duration_seconds=upload.duration_seconds,
            ),
        )

    def complete_video_upload(
        self,
        session: Session,
        background_tasks: BackgroundTasks,
        *,
        post_id: UUID,
        upload_id: UUID,
        payload: VideoUploadCompleteRequest,
    ) -> PostResponse:
        """Finalize an upload, persist processing state, and enqueue transcoding."""

        post = self._get_required_video_post(session, post_id)
        upload = self.repository.get_upload_for_post(session, post_id=post_id, upload_id=upload_id)
        if upload is None:
            raise VideoUploadNotFoundError("Video upload not found")
        if upload.status is not upload.status.PENDING_UPLOAD:
            raise PostValidationError("Video upload has already been completed")

        upload.status = upload.status.COMPLETED
        post.status = PostStatus.PROCESSING
        self.repository.upsert_video_asset(
            session,
            post=post,
            upload=upload,
            source_key=payload.source_key,
        )
        session.commit()

        background_tasks.add_task(self.processor.process_post_video, post.id)

        loaded_post = self.repository.get_post_by_id(session, post.id)
        if loaded_post is None:
            raise PostValidationError("Completed post could not be loaded")
        return self._serialize_post(loaded_post)

    def get_post(self, session: Session, post_id: UUID) -> PostResponse:
        """Return a serialized post detail response."""

        post = self.repository.get_post_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")
        return self._serialize_post(post)

    def list_user_feed(
        self,
        session: Session,
        *,
        user_id: UUID,
        page: int,
        limit: int,
    ) -> PostListResponse:
        """Return a user's feed with surrounding items intact."""

        if self.user_repository.get_by_id(session, user_id) is None:
            raise UserNotFoundError("User not found")

        offset = (page - 1) * limit
        posts = self.repository.list_posts_for_user(
            session,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
        total = self.repository.count_posts_for_user(session, user_id=user_id)
        return PostListResponse(
            items=[self._serialize_post(post) for post in posts],
            page=page,
            limit=limit,
            total=total,
        )

    def _get_required_video_post(self, session: Session, post_id: UUID) -> Post:
        post = self.repository.get_post_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")
        if post.post_type is not PostType.VIDEO:
            raise PostValidationError("Video uploads are only supported for video posts")
        return post

    def _validate_upload_asset(self, asset: VideoAssetInput) -> None:
        if asset.mime_type not in set(self.settings.video_upload_allowed_mime_types):
            raise VideoUploadValidationError(
                VideoUploadFailureCode.UNSUPPORTED_FORMAT,
                "Video format is not supported",
            )
        if asset.video_codec not in set(self.settings.video_upload_allowed_video_codecs):
            raise VideoUploadValidationError(
                VideoUploadFailureCode.UNSUPPORTED_FORMAT,
                "Video format is not supported",
            )
        if asset.audio_codec not in set(self.settings.video_upload_allowed_audio_codecs):
            raise VideoUploadValidationError(
                VideoUploadFailureCode.UNSUPPORTED_AUDIO_CODEC,
                "Audio format is not supported",
            )
        if asset.file_size_bytes > self.settings.video_upload_max_size_bytes:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.FILE_TOO_LARGE,
                "Video file exceeds the configured size limit",
            )
        if asset.duration_seconds > self.settings.video_upload_max_duration_seconds:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.DURATION_TOO_LONG,
                "Video duration exceeds the configured limit",
            )

    def _build_upload_path(self, post_id: UUID, filename: str) -> str:
        sanitized_filename = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "video.mp4"
        return (
            f"{self.settings.video_upload_storage_prefix.rstrip('/')}/"
            f"{post_id}/{sanitized_filename}"
        )

    def _serialize_post(self, post: Post) -> PostResponse:
        video_asset = None
        if post.video_asset is not None:
            asset = post.video_asset
            video_asset = VideoAssetResponse(
                id=asset.id,
                upload_id=asset.upload_id,
                source_key=asset.source_key,
                file_name=asset.file_name,
                mime_type=asset.mime_type,
                status=asset.status,
                is_playable=asset.is_playable,
                playback_metadata=asset.playback_metadata,
                poster_metadata=asset.poster_metadata,
                thumbnail_metadata=asset.thumbnail_metadata,
                failure_reason=asset.failure_reason,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )

        return PostResponse(
            id=post.id,
            user_id=post.user_id,
            post_type=post.post_type,
            caption=post.caption,
            status=post.status,
            video_asset=video_asset,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
