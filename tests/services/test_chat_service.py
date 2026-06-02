"""Unit tests for the chat service."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

from app.chat.models import ConversationTurn, RetrievedPost
from app.chat.schemas import ChatRequest
from app.chat.service import ChatPrompt, ChatService
from app.chat.session_store import InMemorySessionContextStore


class RecordingRetriever:
    """Test retriever that records every query."""

    def __init__(self, responses: dict[str, list[RetrievedPost]]) -> None:
        self.responses = responses
        self.calls: list[tuple[UUID, str]] = []

    def retrieve_posts(self, *, user_id: UUID, query: str) -> Sequence[RetrievedPost]:
        """Return configured evidence for the query."""

        self.calls.append((user_id, query))
        return self.responses.get(query, [])


class RecordingResponder:
    """Test responder that records prompt construction."""

    def __init__(self) -> None:
        self.prompts: list[ChatPrompt] = []

    def generate_reply(self, prompt: ChatPrompt) -> str:
        """Return a deterministic answer for assertions."""

        self.prompts.append(prompt)
        return f"answer:{prompt.question}"


def build_request(*, user_id: UUID, session_id: str, message: str) -> ChatRequest:
    """Return a chat request payload for tests."""

    return ChatRequest(user_id=user_id, session_id=session_id, message=message)


def test_follow_up_reuses_recent_context_and_retrieves_fresh_evidence() -> None:
    """A follow-up turn should see prior context and still retrieve again."""

    user_id = uuid4()
    retriever = RecordingRetriever(
        {
            "First question": [RetrievedPost(post_id="post-1", content="first evidence")],
            "Follow up": [RetrievedPost(post_id="post-2", content="fresh follow-up evidence")],
        }
    )
    responder = RecordingResponder()
    service = ChatService(
        retriever=retriever,
        responder=responder,
        session_store=InMemorySessionContextStore(max_turns=3),
    )

    first_response = service.answer(
        build_request(user_id=user_id, session_id="session-a", message="First question")
    )
    second_response = service.answer(
        build_request(user_id=user_id, session_id="session-a", message="Follow up")
    )

    assert first_response.history_turns_used == 0
    assert second_response.history_turns_used == 1
    assert retriever.calls == [(user_id, "First question"), (user_id, "Follow up")]
    assert responder.prompts[1].prior_turns == [
        ConversationTurn(
            user_message="First question",
            assistant_message="answer:First question",
        )
    ]
    assert [item.post_id for item in second_response.evidence] == ["post-2"]


def test_new_session_does_not_reuse_context_from_another_session() -> None:
    """Different session ids should remain isolated."""

    user_id = uuid4()
    retriever = RecordingRetriever({"Question": [], "Fresh session": []})
    responder = RecordingResponder()
    service = ChatService(
        retriever=retriever,
        responder=responder,
        session_store=InMemorySessionContextStore(max_turns=3),
    )

    service.answer(build_request(user_id=user_id, session_id="session-a", message="Question"))
    response = service.answer(
        build_request(user_id=user_id, session_id="session-b", message="Fresh session")
    )

    assert response.history_turns_used == 0
    assert responder.prompts[1].prior_turns == []


def test_retention_window_trims_oldest_turns_first() -> None:
    """Only the configured number of completed turns should be retained per session."""

    user_id = uuid4()
    retriever = RecordingRetriever({})
    responder = RecordingResponder()
    session_store = InMemorySessionContextStore(max_turns=2)
    service = ChatService(
        retriever=retriever,
        responder=responder,
        session_store=session_store,
    )

    service.answer(build_request(user_id=user_id, session_id="session-a", message="turn-1"))
    service.answer(build_request(user_id=user_id, session_id="session-a", message="turn-2"))
    service.answer(build_request(user_id=user_id, session_id="session-a", message="turn-3"))

    assert list(session_store.get_all_turns("session-a")) == [
        ConversationTurn(user_message="turn-2", assistant_message="answer:turn-2"),
        ConversationTurn(user_message="turn-3", assistant_message="answer:turn-3"),
    ]
