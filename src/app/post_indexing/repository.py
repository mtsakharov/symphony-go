"""Repository layer for indexed post chunks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.post_indexing.models import PostIndexRecord
from app.post_indexing.schemas import IndexedPostChunk


class PostIndexRepository:
    """Persist and replace post index records."""

    def replace_post_chunks(
        self,
        session: Session,
        *,
        user_id: UUID,
        post_id: UUID,
        chunks: list[IndexedPostChunk],
    ) -> None:
        """Replace the stored chunk set for a single post."""

        self.delete_post_chunks(session, user_id=user_id, post_id=post_id)
        if not chunks:
            return

        session.add_all(
            PostIndexRecord(
                user_id=chunk.user_id,
                post_id=chunk.post_id,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=chunk.embedding,
                visibility=chunk.visibility,
                source_created_at=chunk.source_created_at,
                source_updated_at=chunk.source_updated_at,
                source_published_at=chunk.source_published_at,
            )
            for chunk in chunks
        )
        session.flush()

    def delete_post_chunks(self, session: Session, *, user_id: UUID, post_id: UUID) -> int:
        """Delete all stored chunks for a single post."""

        ids_statement = select(PostIndexRecord.id).where(
            PostIndexRecord.user_id == user_id,
            PostIndexRecord.post_id == post_id,
        )
        record_ids = list(session.execute(ids_statement).scalars().all())
        if not record_ids:
            return 0

        delete_statement = delete(PostIndexRecord).where(PostIndexRecord.id.in_(record_ids))
        session.execute(delete_statement)
        return len(record_ids)

    def list_post_chunks(self, session: Session, *, user_id: UUID) -> list[PostIndexRecord]:
        """Return all indexed chunks for a single user."""

        statement = (
            select(PostIndexRecord)
            .where(PostIndexRecord.user_id == user_id)
            .order_by(PostIndexRecord.post_id.asc(), PostIndexRecord.chunk_index.asc())
        )
        return list(session.execute(statement).scalars().all())
