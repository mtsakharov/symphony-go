"""Search gateway abstractions for retrieval."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.posts.models import Post
from app.retrieval.schemas import SearchHit


class SearchGateway(Protocol):
    """Protocol for a user-scoped retrieval backend."""

    def search(
        self,
        session: Session,
        *,
        user_id: UUID,
        query_text: str,
        limit: int,
    ) -> list[SearchHit]:
        """Return ranked post candidates scoped to a single user."""


class SqlPostSearchGateway:
    """Simple SQL-backed search adapter for indexed post content."""

    def search(
        self,
        session: Session,
        *,
        user_id: UUID,
        query_text: str,
        limit: int,
    ) -> list[SearchHit]:
        """Return ranked candidates using strict user scoping."""

        terms = _normalize_terms(query_text)
        if not terms or limit <= 0:
            return []

        statement = _build_statement(user_id=user_id, terms=terms)
        posts = list(session.execute(statement).scalars().all())

        ranked_posts = sorted(
            posts,
            key=lambda post: (_score_post(post.content, terms), post.updated_at, post.id),
            reverse=True,
        )[:limit]

        hits: list[SearchHit] = []
        for index, post in enumerate(ranked_posts, start=1):
            snippet, source_start, source_end = _build_snippet(post.content, terms)
            hits.append(
                SearchHit(
                    post_id=post.id,
                    owner_user_id=post.user_id,
                    score=_score_post(post.content, terms),
                    search_rank=index,
                    snippet=snippet,
                    source_start=source_start,
                    source_end=source_end,
                )
            )

        return hits


def _normalize_terms(query_text: str) -> list[str]:
    """Normalize a free-form query into search terms."""

    return [term for term in query_text.lower().split() if term]


def _build_statement(*, user_id: UUID, terms: Iterable[str]) -> Select[tuple[Post]]:
    """Build a user-scoped candidate query."""

    predicates = [func.lower(Post.content).contains(term) for term in terms]
    return select(Post).where(Post.user_id == user_id, or_(*predicates))


def _score_post(content: str, terms: Iterable[str]) -> float:
    """Compute a simple lexical relevance score."""

    lowered = content.lower()
    return float(sum(lowered.count(term) for term in terms))


def _build_snippet(
    content: str,
    terms: list[str],
    *,
    snippet_length: int = 240,
) -> tuple[str, int, int]:
    """Extract a snippet around the first matching term."""

    lowered = content.lower()
    match_start = 0
    for term in terms:
        index = lowered.find(term)
        if index >= 0:
            match_start = index
            break

    half_length = snippet_length // 2
    start = max(match_start - half_length, 0)
    end = min(start + snippet_length, len(content))
    snippet = content[start:end].strip()
    return snippet or content[:snippet_length].strip(), start, end
