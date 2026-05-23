"""Redis content-hash result cache for AI provider calls.

A cache hit means: same input chunks + same prompt version + same model.
Used by orchestrator stages (analyze, generate_section, judge, embed) so that
replaying a QuestionSet with an unchanged stage skips the provider call.

Cached payloads are stored as JSON strings under keys of the form:
    ai:cache:{namespace}:{sha256}

TTL is configurable via settings.ai_cache_ttl_seconds (default 24h).

The cache is opt-in per call site — only stable stages should use it. Stages
with randomness (e.g. judge with temperature > 0) should pass `enabled=False`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.ai.redis_client import get_redis
from app.core.config import settings


def hash_key(*parts: Any) -> str:
    """Deterministic SHA256 of the JSON-serialized parts.

    `parts` typically includes (chunk_text, prompt_version_id_str, model, provider).
    Order matters; pass them in a consistent order at every call site.
    """
    serialized = json.dumps(
        [p if isinstance(p, (str, int, float, bool, type(None))) else str(p) for p in parts],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


async def get(namespace: str, key: str) -> dict[str, Any] | None:
    """Return cached JSON payload or None."""
    redis_key = f"ai:cache:{namespace}:{key}"
    try:
        raw = await get_redis().get(redis_key)
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def set(
    namespace: str,
    key: str,
    payload: dict[str, Any],
    *,
    ttl_seconds: int | None = None,
) -> None:
    """Store JSON payload under (namespace, key) with TTL. Silently no-ops on failure."""
    redis_key = f"ai:cache:{namespace}:{key}"
    ttl = ttl_seconds if ttl_seconds is not None else settings.ai_cache_ttl_seconds
    try:
        await get_redis().set(redis_key, json.dumps(payload), ex=ttl)
    except Exception:
        # Cache failures must never bubble up — degrade to no-cache.
        pass


async def invalidate(namespace: str, key: str) -> None:
    """Force-evict one entry. Used by admins via Phase 6."""
    redis_key = f"ai:cache:{namespace}:{key}"
    try:
        await get_redis().delete(redis_key)
    except Exception:
        pass
