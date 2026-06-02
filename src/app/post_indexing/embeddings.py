"""Embedding helpers for post indexing."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")


class EmbeddingGenerator(Protocol):
    """Protocol for pluggable embedding generation."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input document."""


@dataclass(frozen=True, slots=True)
class DeterministicEmbeddingGenerator:
    """Dependency-free embedding generator used when no external vector stack exists."""

    dimensions: int = 16

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate stable vectors for each document."""

        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        """Project token hashes into a fixed-size normalized vector."""

        vector = [0.0] * self.dimensions
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:2], byteorder="big") % self.dimensions
            direction = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[bucket] += direction

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return vector
        return [round(value / magnitude, 6) for value in vector]
