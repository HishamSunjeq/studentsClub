"""Cross-encoder rerankers for top-tier RAG (Phase 4).

Hybrid retrieval (dense + sparse, RRF-fused) returns a wide candidate
set; the reranker scores each candidate against the original query
using a dedicated reranking model and keeps the top-N. This is what
turns "good recall" into "good precision."
"""

from app.ai.rag.reranker.base import RerankCandidate, RerankResult, Reranker

__all__ = ["Reranker", "RerankCandidate", "RerankResult"]
