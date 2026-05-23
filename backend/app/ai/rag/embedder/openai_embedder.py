"""OpenAI dense embedder — text-embedding-3-small by default (Phase 3).

Batched (<= 100 per request), retry-on-transient (handled by the SDK +
worker-level retry), and telemetry-logged by the caller.
"""

from __future__ import annotations

import logging
from typing import Iterable

from openai import AsyncOpenAI

from app.ai.rag import EMBEDDING_VERSION

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dim: int = 1536,
    ) -> None:
        self.name = f"openai/{model}"
        self.model = model
        self.dim = dim
        self.version = EMBEDDING_VERSION
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for batch in _batched(texts, 96):
            resp = await self._client.embeddings.create(model=self.model, input=batch)
            out.extend(d.embedding for d in resp.data)
        return out


def _batched(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]
