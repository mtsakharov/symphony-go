"""HTTP client for the upstream posts chat API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from app.chat.exceptions import ChatConfigurationError, ChatUpstreamError
from app.core.config import Settings


class PostsChatClient:
    """Call the upstream posts chat API."""

    def __init__(
        self,
        *,
        base_url: str,
        posts_path: str,
        timeout_seconds: float,
        token: str | None,
        token_header: str,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._posts_path = posts_path
        self._timeout_seconds = timeout_seconds
        self._token = token
        self._token_header = token_header

    @classmethod
    def from_settings(cls, settings: Settings) -> PostsChatClient:
        """Build a client from application settings."""

        return cls(
            base_url=settings.chat_api_base_url,
            posts_path=settings.chat_api_posts_path,
            timeout_seconds=settings.chat_api_timeout_seconds,
            token=settings.chat_api_token,
            token_header=settings.chat_api_token_header,
        )

    async def ask_posts_question(
        self,
        *,
        question: str,
        session_id: str | None,
        forwarded_headers: Mapping[str, str],
    ) -> dict[str, Any]:
        """Send a posts question to the upstream API and return the JSON payload."""

        if not self._base_url:
            raise ChatConfigurationError()

        payload: dict[str, str] = {"question": question}
        if session_id is not None:
            payload["session_id"] = session_id

        headers = dict(forwarded_headers)
        normalized_header_names = {name.lower() for name in headers}
        if self._token and self._token_header.lower() not in normalized_header_names:
            headers[self._token_header] = self._token

        url = f"{self._base_url}/{self._posts_path.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ChatUpstreamError(
                f"Chat API returned {exc.response.status_code} for {self._posts_path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChatUpstreamError("Chat API request failed") from exc

        data = response.json()
        if not isinstance(data, dict):
            raise ChatUpstreamError("Chat API returned an invalid payload")
        return data
