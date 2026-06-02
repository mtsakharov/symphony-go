"""Service layer for per-user post indexing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.post_indexing.chunking import chunk_normalized_text, normalize_post_content
from app.post_indexing.embeddings import DeterministicEmbeddingGenerator, EmbeddingGenerator
from app.post_indexing.repository import PostIndexRepository
from app.post_indexing.schemas import IndexedPostChunk, PostIndexingSummary, SourcePost
from app.posts.models import Post
from app.posts.repository import PostRepository


class UserPostIndexingService:
    """Index the eligible posts for a single user."""

    def __init__(
        self,
        *,
        post_repository: PostRepository | None = None,
        index_repository: PostIndexRepository | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
        max_chunk_size: int = 800,
    ) -> None:
        self.post_repository = post_repository or PostRepository()
        self.index_repository = index_repository or PostIndexRepository()
        self.embedding_generator = embedding_generator or DeterministicEmbeddingGenerator()
        self.max_chunk_size = max_chunk_size

    def index_user_posts(self, session: Session, user_id: UUID) -> PostIndexingSummary:
        """Index all eligible posts for one user and remove stale ineligible chunks."""

        indexed_posts = 0
        skipped_posts = 0
        removed_posts = 0
        indexed_chunks = 0

        try:
            for post_model in self.post_repository.list_for_user(session, user_id):
                post = _to_source_post(post_model)
                normalized_content = normalize_post_content(title=post.title, body=post.body)

                if not _is_eligible(post, normalized_content):
                    if self.index_repository.delete_post_chunks(
                        session,
                        user_id=user_id,
                        post_id=post.id,
                    ):
                        removed_posts += 1
                    skipped_posts += 1
                    continue

                chunks = chunk_normalized_text(
                    post_id=post.id,
                    text=normalized_content,
                    max_chars=self.max_chunk_size,
                )
                embeddings = self.embedding_generator.embed_documents(
                    [chunk.text for chunk in chunks]
                )
                self.index_repository.replace_post_chunks(
                    session,
                    user_id=user_id,
                    post_id=post.id,
                    chunks=[
                        IndexedPostChunk(
                            user_id=post.user_id,
                            post_id=post.id,
                            chunk_id=chunk.chunk_id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.text,
                            embedding=embedding,
                            visibility=post.visibility,
                            source_created_at=post.created_at,
                            source_updated_at=post.updated_at,
                            source_published_at=post.published_at,
                        )
                        for chunk, embedding in zip(chunks, embeddings, strict=True)
                    ],
                )
                indexed_posts += 1
                indexed_chunks += len(chunks)

            session.commit()
        except Exception:
            session.rollback()
            raise

        return PostIndexingSummary(
            user_id=user_id,
            indexed_posts=indexed_posts,
            skipped_posts=skipped_posts,
            removed_posts=removed_posts,
            indexed_chunks=indexed_chunks,
        )


def _is_eligible(post: SourcePost, normalized_content: str) -> bool:
    """Apply the v1 eligibility rules for indexing."""

    return (
        post.published_at is not None
        and not post.is_archived
        and not post.is_deleted
        and bool(normalized_content)
    )


def _to_source_post(post: Post) -> SourcePost:
    """Project the ORM model into the indexing payload."""

    return SourcePost(
        id=post.id,
        user_id=post.user_id,
        title=post.title,
        body=post.body,
        visibility=post.visibility,
        created_at=post.created_at,
        updated_at=post.updated_at,
        published_at=post.published_at,
        is_archived=post.is_archived,
        is_deleted=post.is_deleted,
    )
