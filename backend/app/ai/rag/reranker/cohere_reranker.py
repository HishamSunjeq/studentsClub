"""Cohere Rerank v3 implementation (Phase 4).

Uses Cohere's `rerank` HTTP endpoint. We talk to it via httpx rather
than adding the official `cohere` SDK — the API is a single POST and
the SDK pulls in a heavier dependency tree.
"""

from __future__ import annotations

import logging

import httpx

from app.ai.rag.reranker.base import RerankCandidate, RerankResult

logger = logging.getLogger(__name__)

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"


class CohereReranker:
    def __init__(self, *, api_key: str, model: str = "rerank-v3.5", timeout: float = 30.0) -> None:
        self.name = "cohere"
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
        if not candidates:
            return []
        if top_n <= 0:
            return []

        payload = {
            "model": self.model,
            "query": query,
            "documents": [c.text for c in candidates],
            "top_n": min(top_n, len(candidates)),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(COHERE_RERANK_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[RerankResult] = []
        for r in data.get("results", []):
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
