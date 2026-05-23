"""BM25 sparse encoder via fastembed (Phase 3).

Runs locally on CPU — no API call. Lazy-initialized because the model
download is ~50 MB. `encode` returns a list of (indices, values) tuples
ready for Qdrant `SparseVector`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass
class SparseVec:
    indices: list[int]
    values: list[float]


class BM25SparseEncoder:
    name = "bm25"
    version = "v1"

    def __init__(self, model_name: str = "Qdrant/bm25") -> None:
        self.model_name = model_name
        self._model = None
        self._lock = asyncio.Lock()

    async def _load(self):
        if self._model is None:
            async with self._lock:
                if self._model is None:
                    from fastembed import SparseTextEmbedding

                    self._model = await asyncio.to_thread(
                        SparseTextEmbedding, model_name=self.model_name
                    )
                    logger.info("Loaded BM25 sparse encoder %s", self.model_name)
        return self._model

    async def encode(self, texts: list[str]) -> list[SparseVec]:
        if not texts:
            return []
        model = await self._load()
        # fastembed is sync — push to a thread pool.
        embs = await asyncio.to_thread(_to_list, model.embed(texts))
        out: list[SparseVec] = []
        for e in embs:
            indices = e.indices.tolist() if hasattr(e.indices, "tolist") else list(e.indices)
            values = e.values.tolist() if hasattr(e.values, "tolist") else list(e.values)
            out.append(SparseVec(indices=indices, values=values))
        return out


def _to_list(iterable: Iterable) -> list:
    return list(iterable)
