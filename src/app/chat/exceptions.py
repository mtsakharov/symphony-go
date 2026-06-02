"""Chat domain exceptions."""

from __future__ import annotations


class ChatError(Exception):
    """Base class for chat integration errors."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class ChatConfigurationError(ChatError):
    """Raised when the upstream chat dependency is not configured."""

    def __init__(self, message: str = "Chat API is not configured") -> None:
        super().__init__(message, status_code=503)


class ChatUpstreamError(ChatError):
    """Raised when the upstream chat dependency fails or returns invalid data."""

    def __init__(self, message: str = "Chat API request failed") -> None:
        super().__init__(message, status_code=502)
