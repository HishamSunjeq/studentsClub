"""DB-backed prompt loader with a small in-process TTL cache (Phase 2).

`get_active_prompt(name)` returns the active version. Cached for 60s so
the per-request lookup is essentially free. Bumping a prompt to a new
active version is admin-side; readers pick it up within a minute.

Falls back to the hardcoded `EXTRACTION_SYSTEM_PROMPT` in
`app.ai.prompts` for `extraction.system` if the DB hasn't been migrated
yet (i.e. tests, fresh dev databases). That keeps the old behavior
intact while Phase 2 rolls out.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.ai_prompt import AIPrompt

_CACHE_TTL_SECONDS = 60.0


@dataclass
class PromptRecord:
    id: uuid.UUID
    name: str
    version: int
    role: str
    content: str
    model_hint: str | None


_cache: dict[str, tuple[float, PromptRecord]] = {}
_lock = asyncio.Lock()


async def get_active_prompt(name: str) -> PromptRecord:
    """Return the active version of `name`, cached for 60s."""
    now = time.monotonic()
    cached = _cache.get(name)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    async with _lock:
        cached = _cache.get(name)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        record = await _load_from_db(name)
        if record is None:
            record = _fallback(name)
        if record is None:
            raise KeyError(f"No active prompt found for name {name!r}")

        _cache[name] = (time.monotonic(), record)
        return record


def invalidate(name: str | None = None) -> None:
    """Drop cached entries. Called by the admin API after activate/rollback."""
    if name is None:
        _cache.clear()
    else:
        _cache.pop(name, None)


async def _load_from_db(name: str) -> PromptRecord | None:
    try:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(
                    select(AIPrompt).where(
                        AIPrompt.name == name,
                        AIPrompt.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return PromptRecord(
                id=row.id,
                name=row.name,
                version=row.version,
                role=row.role,
                content=row.content,
                model_hint=row.model_hint,
            )
    except Exception:
        # Treat DB issues (e.g. tests without Postgres) as "not found" so we
        # can fall back to the hardcoded prompt.
        return None


def _fallback(name: str) -> PromptRecord | None:
    if name == "extraction.system":
        from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT

        return PromptRecord(
            id=uuid.UUID(int=0),
            name=name,
            version=0,
            role="system",
            content=EXTRACTION_SYSTEM_PROMPT,
            model_hint=None,
        )
    return None
