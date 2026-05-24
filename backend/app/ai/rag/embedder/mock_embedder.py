"""Mock embedder for `AI_PROVIDER=mock` dev mode.

Returns deterministic pseudo-random unit vectors so the indexing pipeline
runs end-to-end without an OpenAI key. Vectors are reproducible from the
text content (hash-seeded), so re-embedding the same chunk yields the
same vector and dedup behaves stably across runs.
"""

from __future__ import annotations

import hashlib
import math

from app.ai.rag import EMBEDDING_VERSION


class MockEmbedder:
    def __init__(self, *, model: str = "mock-embed", dim: int = 1536) -> None:
        self.name = f"mock/{model}"
        self.model = model
        self.dim = dim
        self.version = EMBEDDING_VERSION

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_pseudo_vector(t, self.dim) for t in texts]


def _pseudo_vector(text: str, dim: int) -> list[float]:
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    # Stretch the 32-byte digest across `dim` floats in [-1, 1).
    vec: list[float] = []
    i = 0
    while len(vec) < dim:
        b = seed[i % len(seed)]
        vec.append((b / 127.5) - 1.0)
        i += 1
    # L2-normalize so cosine similarity is well-behaved.
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
