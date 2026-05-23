"""Reranker Protocol (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class RerankCandidate:
    """One document up for reranking. `id` is opaque to the reranker;
    the orchestrator uses it to thread chunk IDs through.
    """

    id: str
    text: str


@dataclass
class RerankResult:
    id: str
    score: float
    index: int  # original index in the input candidates list


@runtime_checkable
class Reranker(Protocol):
    name: str
    model: str

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        ...
