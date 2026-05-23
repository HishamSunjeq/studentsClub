"""AI pipeline event bus over Redis pub/sub (Phase 4 / 5).

Each stage publishes one event per state transition; the SSE endpoint
(`GET /api/v1/uploads/{id}/events`) subscribes to the channel and
streams events to the browser.

`safe_publish` swallows all errors — events are observability, not
correctness, and a transient Redis blip must not kill a generation.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def channel_for_upload(upload_id: uuid.UUID | str) -> str:
    return f"ai:events:{upload_id}"


def channel_for_chat(session_id: uuid.UUID | str) -> str:
    return f"subject:chat:{session_id}"


async def publish(channel: str, event: dict[str, Any]) -> None:
    """Publish one event to a pub/sub channel. Caller must wrap in try/except
    if they want fire-and-forget; use `safe_publish` for that.
    """
    from app.ai.redis_client import get_redis

    if "ts" not in event:
        event["ts"] = datetime.now(timezone.utc).isoformat()
    client = get_redis()
    await client.publish(channel, json.dumps(event, default=str))


async def safe_publish(upload_id: uuid.UUID | str, event: dict[str, Any]) -> None:
    """Best-effort publish to the upload's event channel."""
    try:
        await publish(channel_for_upload(upload_id), event)
    except Exception:
        logger.debug("ai_events: publish failed for upload=%s", upload_id, exc_info=True)


async def safe_publish_chat(session_id: uuid.UUID | str, event: dict[str, Any]) -> None:
    try:
        await publish(channel_for_chat(session_id), event)
    except Exception:
        logger.debug("ai_events: chat publish failed for session=%s", session_id, exc_info=True)
