"""Unit tests for retrieval service behavior."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.posts.models import Post
from app.posts.repository import PostRepository
from app.retrieval.schemas import SearchHit
from app.retrieval.service import RetrievalService
from app.users.models import User


class StubSearchGateway:
    """Test double for the search gateway."""

    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls: list[dict[str, object]] = []

    def search(
        self,
        session: Session,
        *,
        user_id: UUID,
        query_text: str,
        limit: int,
    ) -> list[SearchHit]:
        """Return the configured hits and record the invocation."""

        self.calls.append(
            {
                "session": session,
                "user_id": user_id,
                "query_text": query_text,
                "limit": limit,
            }
        )
        return self.hits[:limit]


def create_user(session: Session, *, email: str) -> User:
    """Persist a user for retrieval tests."""

    user = User(email=email, first_name="Test", last_name="User")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_post(
    session: Session,
    *,
    user_id: UUID,
    content: str,
    is_deleted: bool = False,
    is_private: bool = False,
    is_blocked: bool = False,
) -> Post:
    """Persist a post for retrieval tests."""

    post = Post(
        user_id=user_id,
        content=content,
        is_deleted=is_deleted,
        is_private=is_private,
        is_blocked=is_blocked,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def test_retrieve_filters_cross_user_hits(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Canonical post reads must prevent cross-user leakage."""

    with db_session_factory() as session:
        user = create_user(session, email="owner@example.com")
        other_user = create_user(session, email="other@example.com")
        owner_post = create_post(session, user_id=user.id, content="alpha alpha owner content")
        other_post = create_post(session, user_id=other_user.id, content="alpha other content")

        gateway = StubSearchGateway(
            [
                SearchHit(
                    post_id=other_post.id,
                    owner_user_id=other_user.id,
                    score=12.0,
                    search_rank=1,
                    snippet="alpha leaked content",
                ),
                SearchHit(
                    post_id=owner_post.id,
                    owner_user_id=user.id,
                    score=10.0,
                    search_rank=2,
                    snippet="alpha owner content",
                ),
            ]
        )
        service = RetrievalService(
            post_repository=PostRepository(),
            search_gateway=gateway,
            default_top_k=3,
            max_top_k=10,
            candidate_overfetch=2,
            default_token_budget=20,
        )

        result = service.retrieve(
            session,
            user_id=user.id,
            query_text="alpha",
            top_k=3,
            token_budget=20,
        )

        assert gateway.calls == [
            {
                "session": session,
                "user_id": user.id,
                "query_text": "alpha",
                "limit": 5,
            }
        ]
        assert [record.post_id for record in result.evidence] == [owner_post.id]
        assert result.dropped_ineligible_count == 1
        assert result.eligible_candidate_count == 1


def test_retrieve_excludes_ineligible_posts(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Deleted, private, and blocked posts must be filtered at request time."""

    with db_session_factory() as session:
        user = create_user(session, email="eligible@example.com")
        visible_post = create_post(session, user_id=user.id, content="match visible content")
        deleted_post = create_post(
            session,
            user_id=user.id,
            content="match deleted content",
            is_deleted=True,
        )
        private_post = create_post(
            session,
            user_id=user.id,
            content="match private content",
            is_private=True,
        )
        blocked_post = create_post(
            session,
            user_id=user.id,
            content="match blocked content",
            is_blocked=True,
        )

        gateway = StubSearchGateway(
            [
                SearchHit(
                    post_id=visible_post.id,
                    owner_user_id=user.id,
                    score=9.0,
                    search_rank=1,
                    snippet="visible content",
                ),
                SearchHit(
                    post_id=deleted_post.id,
                    owner_user_id=user.id,
                    score=8.0,
                    search_rank=2,
                    snippet="deleted content",
                ),
                SearchHit(
                    post_id=private_post.id,
                    owner_user_id=user.id,
                    score=7.0,
                    search_rank=3,
                    snippet="private content",
                ),
                SearchHit(
                    post_id=blocked_post.id,
                    owner_user_id=user.id,
                    score=6.0,
                    search_rank=4,
                    snippet="blocked content",
                ),
            ]
        )
        service = RetrievalService(
            post_repository=PostRepository(),
            search_gateway=gateway,
            default_top_k=5,
            max_top_k=5,
            candidate_overfetch=4,
            default_token_budget=20,
        )

        result = service.retrieve(session, user_id=user.id, query_text="match")

        assert [record.post_id for record in result.evidence] == [visible_post.id]
        assert result.dropped_ineligible_count == 3
        assert result.eligible_candidate_count == 1


def test_retrieve_applies_top_k_and_token_budget(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Retrieval should retain ranking metadata and truncate to the token budget."""

    with db_session_factory() as session:
        user = create_user(session, email="budget@example.com")
        first_post = create_post(session, user_id=user.id, content="one two three four five six")
        second_post = create_post(
            session,
            user_id=user.id,
            content="seven eight nine ten eleven twelve",
        )

        gateway = StubSearchGateway(
            [
                SearchHit(
                    post_id=first_post.id,
                    owner_user_id=user.id,
                    score=5.0,
                    search_rank=1,
                    snippet="one two three four five six",
                ),
                SearchHit(
                    post_id=second_post.id,
                    owner_user_id=user.id,
                    score=4.0,
                    search_rank=2,
                    snippet="seven eight nine ten eleven twelve",
                ),
            ]
        )
        service = RetrievalService(
            post_repository=PostRepository(),
            search_gateway=gateway,
            default_top_k=2,
            max_top_k=2,
            candidate_overfetch=1,
            default_token_budget=8,
        )

        result = service.retrieve(
            session,
            user_id=user.id,
            query_text="two seven",
            top_k=2,
            token_budget=8,
        )

        assert len(result.evidence) == 2
        assert result.evidence[0].search_rank == 1
        assert result.evidence[1].search_rank == 2
        assert result.evidence[0].rank == 1
        assert result.evidence[1].rank == 2
        assert result.evidence[1].snippet == "seven eight"
        assert result.tokens_used == 8
        assert result.truncated is True
        assert result.insufficient_reason == "token_budget_truncated"


def test_retrieve_reports_insufficient_evidence_when_only_ineligible_hits_remain(
    db_session_factory: sessionmaker[Session],
) -> None:
    """The answer layer should be able to detect when nothing usable remains."""

    with db_session_factory() as session:
        user = create_user(session, email="empty@example.com")
        hidden_post = create_post(
            session,
            user_id=user.id,
            content="match hidden content",
            is_private=True,
        )

        gateway = StubSearchGateway(
            [
                SearchHit(
                    post_id=hidden_post.id,
                    owner_user_id=user.id,
                    score=3.0,
                    search_rank=1,
                    snippet="hidden content",
                )
            ]
        )
        service = RetrievalService(
            post_repository=PostRepository(),
            search_gateway=gateway,
            default_top_k=1,
            max_top_k=1,
            candidate_overfetch=1,
            default_token_budget=10,
        )

        result = service.retrieve(session, user_id=user.id, query_text="match")

        assert result.evidence == []
        assert result.has_sufficient_evidence is False
        assert result.insufficient_reason == "no_eligible_posts"
