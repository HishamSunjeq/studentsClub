"""Loader for the global `extraction_settings` row (Phase 9).

Mirrors the prompt-registry loader: a small in-process TTL cache so the
per-upload lookup is cheap, with a graceful fallback to env-derived
defaults when the table is missing (fresh dev DB / tests).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.extraction_settings import ExtractionSettings

_CACHE_TTL_SECONDS = 30.0


@dataclass
class ExtractionConfig:
    backend: str = "unstructured"
    strategy: str = "auto"
    ocr_languages: list[str] = field(default_factory=lambda: ["eng", "ara"])
    extract_tables: bool = True
    hi_res_model_name: str | None = None
    max_characters: int | None = None


_cache: tuple[float, ExtractionConfig] | None = None
_lock = asyncio.Lock()


async def load_extraction_settings() -> ExtractionConfig:
    """Return the global extraction config, cached for 30s."""
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1]

    async with _lock:
        if _cache and time.monotonic() - _cache[0] < _CACHE_TTL_SECONDS:
            return _cache[1]
        cfg = await _load_from_db() or _fallback()
        _cache = (time.monotonic(), cfg)
        return cfg


def invalidate() -> None:
    """Drop the cached config. Called by the admin API after PUT."""
    global _cache
    _cache = None


async def _load_from_db() -> ExtractionConfig | None:
    try:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(select(ExtractionSettings).limit(1))
            ).scalar_one_or_none()
            if row is None:
                return None
            return ExtractionConfig(
                backend=row.backend,
                strategy=row.strategy,
                ocr_languages=list(row.ocr_languages or ["eng"]),
                extract_tables=row.extract_tables,
                hi_res_model_name=row.hi_res_model_name,
                max_characters=row.max_characters,
            )
    except Exception:
        return None


def _fallback() -> ExtractionConfig:
    return ExtractionConfig(backend=settings.extraction_backend)
