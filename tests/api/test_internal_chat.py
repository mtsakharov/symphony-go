"""Tests for the internal chat page."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_internal_chat_page_exposes_expected_hooks(client: AsyncClient) -> None:
    """The internal page should expose form hooks and explain the empty state."""

    response = await client.get("/internal/chat")

    assert response.status_code == 200
    assert 'id="chat-form"' in response.text
    assert 'id="chat-input"' in response.text
    assert 'id="chat-messages"' in response.text
    assert "Ask a question about your posts to start the conversation." in response.text
    assert "requestBody.session_id = activeSessionId;" in response.text
