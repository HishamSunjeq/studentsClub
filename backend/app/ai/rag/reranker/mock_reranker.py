"""Mock reranker for tests and dev when no rerank credential is set (Phase 4).

Preserves the input order, assigns descending scores 1.0 → 0.0+.
"""

from __future__ import annotations

from app.ai.rag.reranker.base import RerankCandidate, RerankResult


class MockReranker:
    name = "mock"
    model = "identity"

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        n = min(top_n, len(candidates))
        if n <= 0:
            return []
        results: list[RerankResult] = []
        for i in range(n):
            score = 1.0 - (i / max(1, n))
            results.append(RerankResult(id=candidates[i].id, score=score, index=i))
        return results
