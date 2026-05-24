"""Factory: resolve an embedder from credentials (Phase 3)."""

from __future__ import annotations

from app.core.config import settings
from app.ai.rag.embedder.mock_embedder import MockEmbedder
from app.ai.rag.embedder.openai_embedder import OpenAIEmbedder


async def get_embedder(
    *,
    provider: str = "openai",
    credential_alias: str | None = None,
    model: str = "text-embedding-3-small",
    dim: int = 1536,
):
    if provider == "mock" or (settings.ai_provider or "").lower() == "mock":
        return MockEmbedder(model=model, dim=dim)

    from app.ai.credentials import resolve as resolve_credential
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        cred = await resolve_credential(db, provider="openai", alias=credential_alias)
    return OpenAIEmbedder(api_key=cred.api_key, model=model, dim=dim)
