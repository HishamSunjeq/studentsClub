"""Reranker factory — resolves provider + credentials (Phase 4)."""

from __future__ import annotations

import logging

from app.ai.rag.reranker.base import Reranker
from app.ai.rag.reranker.cohere_reranker import CohereReranker
from app.ai.rag.reranker.mock_reranker import MockReranker
from app.ai.rag.reranker.voyage_reranker import VoyageReranker

logger = logging.getLogger(__name__)


async def get_reranker(
    *,
    provider: str | None = "cohere",
    credential_alias: str | None = None,
    model: str | None = None,
) -> Reranker:
    """Return a Reranker. Falls back to `MockReranker` when the requested
    provider has no credential — keeps dev environments unblocked.
    """
    if not provider or provider == "mock":
        return MockReranker()

    from app.ai.credentials import resolve as resolve_credential
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            cred = await resolve_credential(db, provider=provider, alias=credential_alias)
    except Exception:
        logger.warning("No reranker credential for provider=%s; using MockReranker", provider)
        return MockReranker()

    if provider == "cohere":
        return CohereReranker(api_key=cred.api_key, model=model or "rerank-v3.5")
    if provider == "voyage":
        return VoyageReranker(api_key=cred.api_key, model=model or "rerank-2")

    logger.warning("Unknown reranker provider=%s; using MockReranker", provider)
    return MockReranker()
