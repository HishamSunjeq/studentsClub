"""Voyage rerank-2 implementation (Phase 4)."""

from __future__ import annotations

import logging

import httpx

from app.ai.rag.reranker.base import RerankCandidate, RerankResult

logger = logging.getLogger(__name__)

VOYAGE_RERANK_URL = "https://api.voyageai.com/v1/rerank"


class VoyageReranker:
    def __init__(self, *, api_key: str, model: str = "rerank-2", timeout: float = 30.0) -> None:
        self.name = "voyage"
        self.model = model
        self._api_key = api_key
        self._timeout = timeout

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        if not candidates or top_n <= 0:
            return []

        payload = {
            "model": self.model,
            "query": query,
            "documents": [c.text for c in candidates],
            "top_k": min(top_n, len(candidates)),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(VOYAGE_RERANK_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[RerankResult] = []
        for r in data.get("data", []):
            idx = int(r["index"])
            if 0 <= idx < len(candidates):
                results.append(
                    RerankResult(
                        id=candidates[idx].id,
                        score=float(r.get("relevance_score", 0.0)),
                        index=idx,
                    )
                )
        return results
