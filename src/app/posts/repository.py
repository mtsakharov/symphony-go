"""Repository helpers for posts, uploads, and video assets."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.posts.models import Post, PostStatus, VideoAsset, VideoAssetStatus, VideoUpload


class PostRepository:
    """Persist and query posts and related video entities."""

    def create_post(self, session: Session, *, post: Post) -> Post:
        """Persist a post."""

        session.add(post)
        session.flush()
        return post

    def get_post_by_id(self, session: Session, post_id: UUID) -> Post | None:
        """Return a fully loaded post by id."""

        statement = (
            select(Post)
            .options(
                selectinload(Post.video_asset).selectinload(VideoAsset.upload),
                selectinload(Post.video_uploads),
            )
            .where(Post.id == post_id)
        )
        return session.execute(statement).scalar_one_or_none()

    def list_posts_for_user(
        self,
        session: Session,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> list[Post]:
        """Return a page of posts for a user ordered newest-first."""

        statement = (
            select(Post)
            .options(
                selectinload(Post.video_asset).selectinload(VideoAsset.upload),
                selectinload(Post.video_uploads),
            )
            .where(Post.user_id == user_id, Post.status != PostStatus.DELETED)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_posts_for_user(self, session: Session, *, user_id: UUID) -> int:
        """Return the total number of non-deleted posts for a user."""

        statement = (
            select(func.count())
            .select_from(Post)
            .where(Post.user_id == user_id, Post.status != PostStatus.DELETED)
        )
        return int(session.execute(statement).scalar_one())

    def create_upload(self, session: Session, *, upload: VideoUpload) -> VideoUpload:
        """Persist an upload intent."""

        session.add(upload)
        session.flush()
        return upload

    def get_upload_for_post(
        self,
        session: Session,
        *,
        post_id: UUID,
        upload_id: UUID,
    ) -> VideoUpload | None:
        """Return an upload intent for a specific post."""

        statement = (
            select(VideoUpload)
            .where(VideoUpload.post_id == post_id, VideoUpload.id == upload_id)
            .options(selectinload(VideoUpload.video_asset))
        )
        return session.execute(statement).scalar_one_or_none()

    def upsert_video_asset(
        self,
        session: Session,
        *,
        post: Post,
        upload: VideoUpload,
        source_key: str,
    ) -> VideoAsset:
        """Create or replace the post's current processing asset."""

        asset = post.video_asset
        if asset is None:
            asset = VideoAsset(
                post=post,
                upload=upload,
                source_key=source_key,
                file_name=upload.filename,
                mime_type=upload.mime_type,
            )
            session.add(asset)
            session.flush()
            return asset

        asset.upload = upload
        asset.source_key = source_key
        asset.file_name = upload.filename
        asset.mime_type = upload.mime_type
        asset.status = VideoAssetStatus.PROCESSING
        asset.is_playable = False
        asset.playback_metadata = None
        asset.poster_metadata = None
        asset.thumbnail_metadata = None
        asset.failure_reason = None
        session.add(asset)
        session.flush()
        return asset
