"""HTTP client for the LangGraph answer flow."""

from __future__ import annotations

from typing import Any, cast

import httpx

from app.chat.exceptions import ChatUpstreamError, MalformedUpstreamResponseError


class LangGraphClient:
    """Thin HTTP adapter around the LangGraph answer flow."""

    def __init__(
        self,
        *,
        api_url: str,
        timeout_seconds: float,
        bearer_token: str | None = None,
    ) -> None:
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.bearer_token = bearer_token

    async def answer_question(
        self,
        *,
        user_id: str,
        question: str,
        session_id: str | None,
    ) -> dict[str, Any]:
        """Submit a question to the LangGraph flow and return the JSON payload."""

        headers: dict[str, str] = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "user_id": user_id,
                        "question": question,
                        "session_id": session_id,
                    },
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ChatUpstreamError("LangGraph returned an unsuccessful response") from exc
        except httpx.HTTPError as exc:
            raise ChatUpstreamError("Unable to reach the LangGraph service") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise MalformedUpstreamResponseError("LangGraph returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise MalformedUpstreamResponseError("LangGraph response must be a JSON object")

        return cast(dict[str, Any], payload)
