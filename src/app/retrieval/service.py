"""Business logic for user-scoped retrieval."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.posts.models import Post
from app.posts.repository import PostRepository
from app.retrieval.schemas import EvidenceRecord, RetrievalResult
from app.retrieval.search import SearchGateway, SqlPostSearchGateway


class RetrievalService:
    """Retrieve eligible user-scoped evidence for answer generation."""

    def __init__(
        self,
        *,
        post_repository: PostRepository | None = None,
        search_gateway: SearchGateway | None = None,
        default_top_k: int = 5,
        max_top_k: int = 10,
        candidate_overfetch: int = 5,
        default_token_budget: int = 400,
    ) -> None:
        self.post_repository = post_repository or PostRepository()
        self.search_gateway = search_gateway or SqlPostSearchGateway()
        self.default_top_k = default_top_k
        self.max_top_k = max_top_k
        self.candidate_overfetch = candidate_overfetch
        self.default_token_budget = default_token_budget

    def retrieve(
        self,
        session: Session,
        *,
        user_id: UUID,
        query_text: str,
        top_k: int | None = None,
        token_budget: int | None = None,
    ) -> RetrievalResult:
        """Return ranked evidence restricted to the authenticated user."""

        applied_top_k = min(top_k or self.default_top_k, self.max_top_k)
        applied_token_budget = token_budget or self.default_token_budget
        candidate_limit = applied_top_k + self.candidate_overfetch

        search_hits = self.search_gateway.search(
            session,
            user_id=user_id,
            query_text=query_text,
            limit=candidate_limit,
        )
        posts_by_id = self._load_posts_by_id(
            session,
            user_id=user_id,
            post_ids=[hit.post_id for hit in search_hits],
        )

        evidence: list[EvidenceRecord] = []
        tokens_used = 0
        eligible_candidate_count = 0
        dropped_ineligible_count = 0
        truncated = False

        for hit in search_hits:
            post = posts_by_id.get(hit.post_id)
            if post is None or not is_post_eligible(post):
                dropped_ineligible_count += 1
                continue

            eligible_candidate_count += 1
            remaining_budget = applied_token_budget - tokens_used
            if remaining_budget <= 0:
                truncated = True
                break

            snippet, token_count, snippet_truncated = truncate_text_to_budget(
                hit.snippet,
                token_budget=remaining_budget,
            )
            if token_count <= 0:
                truncated = True
                break

            evidence.append(
                EvidenceRecord(
                    post_id=hit.post_id,
                    owner_user_id=post.user_id,
                    score=hit.score,
                    rank=len(evidence) + 1,
                    search_rank=hit.search_rank,
                    snippet=snippet,
                    token_count=token_count,
                    source_start=hit.source_start,
                    source_end=hit.source_end,
                )
            )
            tokens_used += token_count
            truncated = truncated or snippet_truncated

            if len(evidence) >= applied_top_k:
                break

        insufficient_reason = determine_insufficient_reason(
            evidence=evidence,
            search_candidate_count=len(search_hits),
            eligible_candidate_count=eligible_candidate_count,
            truncated=truncated,
        )

        return RetrievalResult(
            user_id=user_id,
            query=query_text,
            requested_top_k=top_k or self.default_top_k,
            applied_top_k=applied_top_k,
            token_budget=applied_token_budget,
            tokens_used=tokens_used,
            search_candidate_count=len(search_hits),
            eligible_candidate_count=eligible_candidate_count,
            dropped_ineligible_count=dropped_ineligible_count,
            truncated=truncated,
            has_sufficient_evidence=bool(evidence),
            insufficient_reason=insufficient_reason,
            evidence=evidence,
        )

    def _load_posts_by_id(
        self,
        session: Session,
        *,
        user_id: UUID,
        post_ids: Iterable[UUID],
    ) -> dict[UUID, Post]:
        """Load canonical posts keyed by id."""

        unique_post_ids = list(dict.fromkeys(post_ids))
        posts = self.post_repository.list_by_ids_for_user(
            session,
            post_ids=unique_post_ids,
            user_id=user_id,
        )
        return {post.id: post for post in posts}


def is_post_eligible(post: Post) -> bool:
    """Return whether a post is eligible for retrieval."""

    return not post.is_deleted and not post.is_private and not post.is_blocked


def estimate_token_count(text: str) -> int:
    """Estimate token usage from whitespace-delimited text."""

    return len(text.split())


def truncate_text_to_budget(text: str, *, token_budget: int) -> tuple[str, int, bool]:
    """Trim a snippet to fit within the remaining token budget."""

    if token_budget <= 0:
        return "", 0, False

    words = text.split()
    if len(words) <= token_budget:
        return text, len(words), False

    truncated_words = words[:token_budget]
    return " ".join(truncated_words), len(truncated_words), True


def determine_insufficient_reason(
    *,
    evidence: list[EvidenceRecord],
    search_candidate_count: int,
    eligible_candidate_count: int,
    truncated: bool,
) -> str | None:
    """Return a machine-readable insufficiency reason when relevant."""

    if evidence:
        return "token_budget_truncated" if truncated else None
    if search_candidate_count == 0:
        return "no_search_hits"
    if eligible_candidate_count == 0:
        return "no_eligible_posts"
    return "token_budget_exhausted"
