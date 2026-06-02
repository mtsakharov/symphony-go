"""Process-local bounded session storage for follow-up context."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from app.chat.models import ConversationTurn


class InMemorySessionContextStore:
    """Store the last N completed turn pairs for each session id.

    Once a session exceeds the configured window, the oldest turn pair is
    discarded first so prompt context remains bounded.
    """

    def __init__(self, *, max_turns: int) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        self._max_turns = max_turns
        self._sessions: dict[str, deque[ConversationTurn]] = {}

    @property
    def max_turns(self) -> int:
        """Return the per-session retention window."""

        return self._max_turns

    def get_turns(self, session_id: str) -> list[ConversationTurn]:
        """Return a copy of the retained turns for the session."""

        return list(self._sessions.get(session_id, ()))

    def append_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Append a completed turn and trim to the configured window."""

        turns = self._sessions.setdefault(session_id, deque(maxlen=self._max_turns))
        turns.append(turn)

    def get_all_turns(self, session_id: str) -> Sequence[ConversationTurn]:
        """Return a read-only view for tests and diagnostics."""

        return tuple(self._sessions.get(session_id, ()))
