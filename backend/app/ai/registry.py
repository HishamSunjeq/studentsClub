"""Model registry loader (Phase 2).

Thin wrapper around `ai_models` rows so providers and the orchestrator can
look up context-window / pricing / capability flags without hardcoding
model strings. Cached for 60 seconds.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.ai_model import AIModel, ModelKind

_CACHE_TTL_SECONDS = 60.0


@dataclass
class ModelRecord:
    id: uuid.UUID
    provider: str
    model_id: str
    display_name: str
    kind: str
    context_window: int
    max_output_tokens: int
    input_cost_per_mtoken: Decimal
    output_cost_per_mtoken: Decimal
    supports_streaming: bool
    supports_json_mode: bool
    supports_prompt_cache: bool
    embedding_dim: int | None
    is_active: bool


_cache: dict[tuple[str, str], tuple[float, ModelRecord]] = {}
_lock = asyncio.Lock()


async def get_model(provider: str, model_id: str) -> ModelRecord | None:
    """Return the model record, cached for 60s. None if unknown."""
    key = (provider, model_id)
    now = time.monotonic()
    cached = _cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    async with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        record = await _load(provider, model_id)
        if record is not None:
            _cache[key] = (time.monotonic(), record)
        return record


def invalidate() -> None:
    _cache.clear()


async def _load(provider: str, model_id: str) -> ModelRecord | None:
    try:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(
                    select(AIModel).where(
                        AIModel.provider == provider,
                        AIModel.model_id == model_id,
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return _to_record(row)
    except Exception:
        return None


def _to_record(row: AIModel) -> ModelRecord:
    return ModelRecord(
        id=row.id,
        provider=row.provider,
        model_id=row.model_id,
        display_name=row.display_name,
        kind=row.kind.value if isinstance(row.kind, ModelKind) else str(row.kind),
        context_window=row.context_window,
        max_output_tokens=row.max_output_tokens,
        input_cost_per_mtoken=row.input_cost_per_mtoken,
        output_cost_per_mtoken=row.output_cost_per_mtoken,
        supports_streaming=row.supports_streaming,
        supports_json_mode=row.supports_json_mode,
        supports_prompt_cache=row.supports_prompt_cache,
        embedding_dim=row.embedding_dim,
        is_active=row.is_active,
    )
