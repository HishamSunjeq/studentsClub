"""Shared async Redis client for AI subsystem (rate limits, result cache, pub/sub).

Connection pool is created lazily on first use and cached per event loop.
Uses `settings.redis_url` which is separate from the Celery broker/result
backend so we don't compete for connections.
"""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return a shared async Redis client. Created on first call."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            health_check_interval=30,
        )
    return _client


async def close_redis() -> None:
    """Close the connection pool. Call on FastAPI shutdown."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
