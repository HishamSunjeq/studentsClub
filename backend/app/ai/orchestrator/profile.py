"""Resolve a `GenerationProfile` row into a flat, ready-to-use bundle (Phase 4).

The DB row references models by FK and credentials by alias; this module
flattens it into a `ResolvedProfile` dataclass with concrete provider /
model strings + threshold values that stages can read without touching
the DB again.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import registry
from app.core.config import settings
from app.models.ai_model import AIModel
from app.models.generation_profile import GenerationProfile

logger = logging.getLogger(__name__)

# Last-resort strings if the model registry is empty (no active rows for a kind).
_HARDCODED = {
    "extraction": ("anthropic", "claude-opus-4-7"),
    "judge": ("anthropic", "claude-haiku-4-5"),
    "embedding": ("openai", "text-embedding-3-small"),
    "rerank": ("cohere", "rerank-v3.5"),
}


@dataclass
class ResolvedProfile:
    profile_id: uuid.UUID | None
    name: str

    # Prompts (by name; resolve lazily inside stages).
    extraction_prompt_name: str = "extraction.system"
    judge_prompt_name: str = "judge.rubric"
    hyde_prompt_name: str = "hyde.expand"
    contextualize_prompt_name: str = "contextualize.chunk"

    # Resolved model + provider + credential per stage.
    extraction_provider: str = "anthropic"
    extraction_model: str = "claude-opus-4-7"
    extraction_credential_alias: str | None = None

    judge_provider: str = "anthropic"
    judge_model: str = "claude-haiku-4-5"
    judge_credential_alias: str | None = None

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_credential_alias: str | None = None

    rerank_provider: str | None = "cohere"
    rerank_model: str | None = "rerank-v3.5"
    rerank_credential_alias: str | None = None

    # Knobs.
    target_count: int = 20
    difficulty_mix: dict[str, float] = field(
        default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )
    judge_threshold: float = 6.0
    dedup_threshold: float = 0.92
    top_k_retrieval: int = 50
    top_n_rerank: int = 8
    hybrid_alpha: float = 0.5
    section_concurrency: int = 4


async def load_profile(
    db: AsyncSession,
    *,
    subject_id: uuid.UUID | None,
    profile_id: uuid.UUID | None = None,
) -> ResolvedProfile:
    """Load a profile row + its referenced models, then flatten. Order:

    1. Explicit `profile_id` if provided.
    2. Subject-scoped default (is_default=true, subject_id=...).
    3. Global default (is_default=true, subject_id IS NULL).
    4. Registry-driven default (top active model per kind).
    """
    row: GenerationProfile | None = None

    if profile_id is not None:
        res = await db.execute(
            select(GenerationProfile).where(GenerationProfile.id == profile_id)
        )
        row = res.scalar_one_or_none()

    if row is None and subject_id is not None:
        res = await db.execute(
            select(GenerationProfile).where(
                GenerationProfile.subject_id == subject_id,
                GenerationProfile.is_default.is_(True),
            )
        )
        row = res.scalar_one_or_none()

    if row is None:
        res = await db.execute(
            select(GenerationProfile).where(
                GenerationProfile.subject_id.is_(None),
                GenerationProfile.is_default.is_(True),
            )
        )
        row = res.scalar_one_or_none()

    if row is None:
        return _force_mock_if_enabled(await _registry_default_profile())

    # Fetch referenced models in one shot.
    model_ids = [
        mid
        for mid in (
            row.extraction_model_id,
            row.judge_model_id,
            row.embedding_model_id,
            row.rerank_model_id,
        )
        if mid is not None
    ]
    models_by_id: dict[uuid.UUID, AIModel] = {}
    if model_ids:
        result = await db.execute(select(AIModel).where(AIModel.id.in_(model_ids)))
        for m in result.scalars().all():
            models_by_id[m.id] = m

    async def _pair(mid: uuid.UUID | None, kind: str) -> tuple[str, str]:
        """Resolve (provider, model) for a stage. Pinned FK wins; else the
        registry's top active model for the kind; else the hardcoded last resort.
        """
        m = models_by_id.get(mid) if mid else None
        if m is not None:
            return m.provider, m.model_id
        return await _registry_pair(kind)

    extraction_provider, extraction_model = await _pair(
        row.extraction_model_id, "extraction"
    )
    judge_provider, judge_model = await _pair(row.judge_model_id, "judge")
    embedding_provider, embedding_model = await _pair(
        row.embedding_model_id, "embedding"
    )

    rerank_provider: str | None = None
    rerank_model: str | None = None
    if row.rerank_model_id is not None:
        rerank_provider, rerank_model = await _pair(row.rerank_model_id, "rerank")

    resolved = ResolvedProfile(
        profile_id=row.id,
        name=row.name,
        extraction_prompt_name=row.prompt_name or "extraction.system",
        judge_prompt_name=row.judge_prompt_name or "judge.rubric",
        extraction_provider=extraction_provider,
        extraction_model=extraction_model,
        extraction_credential_alias=row.credential_alias_extraction,
        judge_provider=judge_provider,
        judge_model=judge_model,
        judge_credential_alias=row.credential_alias_judge,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_credential_alias=row.credential_alias_embedding,
        rerank_provider=rerank_provider,
        rerank_model=rerank_model,
        rerank_credential_alias=row.credential_alias_rerank,
        target_count=row.target_count,
        difficulty_mix=_coerce_mix(row.difficulty_mix),
        judge_threshold=float(row.judge_threshold or Decimal("6.0")),
        dedup_threshold=float(row.dedup_threshold or Decimal("0.92")),
        top_k_retrieval=row.top_k_retrieval,
        top_n_rerank=row.top_n_rerank,
        hybrid_alpha=float(row.hybrid_alpha or Decimal("0.5")),
    )
    return _force_mock_if_enabled(resolved)


async def _registry_pair(kind: str) -> tuple[str, str]:
    """Top active model for `kind` from the registry, or hardcoded last resort."""
    rec = await registry.get_default_model(kind)
    if rec is not None:
        return rec.provider, rec.model_id
    return _HARDCODED.get(kind, ("anthropic", "claude-opus-4-7"))


async def _registry_default_profile() -> ResolvedProfile:
    """Build the no-profile-row default entirely from the model registry, so
    activating/reordering models in the admin Models page drives what runs.
    """
    extraction_provider, extraction_model = await _registry_pair("extraction")
    judge_provider, judge_model = await _registry_pair("judge")
    embedding_provider, embedding_model = await _registry_pair("embedding")
    rerank_provider, rerank_model = await _registry_pair("rerank")
    return ResolvedProfile(
        profile_id=None,
        name="default",
        extraction_provider=extraction_provider,
        extraction_model=extraction_model,
        judge_provider=judge_provider,
        judge_model=judge_model,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        rerank_provider=rerank_provider,
        rerank_model=rerank_model,
    )


def _force_mock_if_enabled(p: ResolvedProfile) -> ResolvedProfile:
    if (settings.ai_provider or "").lower() != "mock":
        return p
    p.extraction_provider = "mock"
    p.judge_provider = "mock"
    p.embedding_provider = "mock"
    if p.rerank_provider is not None:
        p.rerank_provider = "mock"
    return p


def _coerce_mix(raw: Any) -> dict[str, float]:
    if isinstance(raw, dict):
        try:
            return {k: float(v) for k, v in raw.items()}
        except Exception:
            pass
    return {"easy": 0.3, "medium": 0.5, "hard": 0.2}
