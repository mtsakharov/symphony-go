"""Normalization and chunking helpers for post indexing."""

from __future__ import annotations

import html
import re
from uuid import UUID

from app.post_indexing.schemas import PostChunk

_BLOCK_BREAK_TAG_PATTERN = re.compile(
    r"(?i)<\s*(?:br\s*/?|/p|/div|/li|/ul|/ol|/blockquote|/h[1-6])\s*>"
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_INLINE_WHITESPACE_PATTERN = re.compile(r"[^\S\r\n]+")


def normalize_post_content(*, title: str, body: str) -> str:
    """Collapse post content into stable plain text ready for indexing."""

    sections = []
    for raw_value in (title, body):
        normalized = _normalize_section(raw_value)
        if normalized:
            sections.append(normalized)
    return "\n\n".join(sections)


def chunk_normalized_text(*, post_id: UUID, text: str, max_chars: int) -> list[PostChunk]:
    """Split normalized text into deterministic chunks within the configured limit."""

    stripped_text = text.strip()
    if not stripped_text:
        return []

    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n{2,}", stripped_text) if paragraph
    ]
    chunk_texts: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        units = _split_large_paragraph(paragraph, max_chars=max_chars)
        for unit in units:
            if not current_parts:
                current_parts = [unit]
                current_length = len(unit)
                continue

            candidate_length = current_length + 2 + len(unit)
            if candidate_length <= max_chars:
                current_parts.append(unit)
                current_length = candidate_length
                continue

            chunk_texts.append("\n\n".join(current_parts))
            current_parts = [unit]
            current_length = len(unit)

    if current_parts:
        chunk_texts.append("\n\n".join(current_parts))

    return [
        PostChunk(chunk_id=f"{post_id}:{chunk_index}", chunk_index=chunk_index, text=chunk_text)
        for chunk_index, chunk_text in enumerate(chunk_texts)
    ]


def _normalize_section(value: str) -> str:
    """Flatten HTML-ish markup while preserving meaningful paragraph breaks."""

    if not value.strip():
        return ""

    plain_text = html.unescape(_HTML_TAG_PATTERN.sub("", _BLOCK_BREAK_TAG_PATTERN.sub("\n", value)))
    normalized_lines: list[str] = []
    previous_blank = False

    for line in plain_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        collapsed = _INLINE_WHITESPACE_PATTERN.sub(" ", line).strip()
        if not collapsed:
            if not previous_blank and normalized_lines:
                normalized_lines.append("")
            previous_blank = True
            continue

        normalized_lines.append(collapsed)
        previous_blank = False

    return "\n".join(normalized_lines).strip()


def _split_large_paragraph(paragraph: str, *, max_chars: int) -> list[str]:
    """Split oversized paragraphs by word boundaries with a deterministic fallback."""

    if len(paragraph) <= max_chars:
        return [paragraph]

    words = paragraph.split()
    if len(words) <= 1:
        return [
            paragraph[index : index + max_chars] for index in range(0, len(paragraph), max_chars)
        ]

    segments: list[str] = []
    current_words: list[str] = []
    current_length = 0

    for word in words:
        if len(word) > max_chars:
            if current_words:
                segments.append(" ".join(current_words))
                current_words = []
                current_length = 0
            segments.extend(
                word[index : index + max_chars] for index in range(0, len(word), max_chars)
            )
            continue

        candidate_length = len(word) if not current_words else current_length + 1 + len(word)
        if candidate_length <= max_chars:
            current_words.append(word)
            current_length = candidate_length
            continue

        segments.append(" ".join(current_words))
        current_words = [word]
        current_length = len(word)

    if current_words:
        segments.append(" ".join(current_words))

    return segments
