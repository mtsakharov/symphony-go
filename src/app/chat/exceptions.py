"""Domain exceptions for chat workflows."""


class ChatError(Exception):
    """Base chat domain error."""


class SessionAccessError(ChatError):
    """Raised when a session does not belong to the authenticated user."""


class ChatUpstreamError(ChatError):
    """Raised when the LangGraph service fails."""


class MalformedUpstreamResponseError(ChatError):
    """Raised when the LangGraph response cannot be normalized."""
