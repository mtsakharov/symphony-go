"""Internal non-versioned routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.chat.page import render_internal_chat_page
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get(
    "/internal/chat",
    response_class=HTMLResponse,
    summary="Internal posts chat page",
    include_in_schema=False,
)
def internal_chat_page(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Return the thin internal posts chat page."""

    return HTMLResponse(
        render_internal_chat_page(api_v1_prefix=settings.api_v1_prefix),
    )
