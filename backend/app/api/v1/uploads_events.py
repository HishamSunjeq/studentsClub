"""Server-Sent Events endpoint for AI generation progress (Phase 5).

`GET /api/v1/uploads/{id}/events?token=<access_jwt>` subscribes to the
Redis pub/sub channel `ai:events:{upload_id}` and streams every stage
transition to the browser as `text/event-stream`.

EventSource cannot set an `Authorization` header, so the access token is
passed as a query param and validated the same way as the bearer flow.
A 15-second heartbeat keeps proxies from closing the idle connection, and
the stream auto-closes on a terminal `generate.completed` / `error` event.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncIterator

import jwt
from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.ai.events import channel_for_upload
from app.ai.redis_client import get_redis
from app.api.deps import DBSession
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_token
from app.models.upload import Upload
from app.models.user import User

router = APIRouter()

_HEARTBEAT_SECONDS = 15
_TERMINAL_EVENTS = {"generate.completed", "error"}


async def _user_from_query_token(token: str, db: DBSession) -> User:
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Access token has expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid access token")
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise UnauthorizedError("Malformed token")
    user = await db.get(User, uuid.UUID(sub))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def _sse(event: dict) -> str:
    """Format a dict as one SSE `data:` frame."""
    return f"data: {json.dumps(event, default=str)}\n\n"


async def _event_stream(
    request: Request, channel: str
) -> AsyncIterator[str]:
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        # Tell the client the stream is live before any pipeline event arrives.
        yield _sse({"type": "stream.open"})
        while True:
            if await request.is_disconnected():
                break
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=_HEARTBEAT_SECONDS
            )
            if message is None:
                # Idle period elapsed — send a comment heartbeat.
                yield ": heartbeat\n\n"
                continue
            data = message.get("data")
            if not data:
                continue
            yield f"data: {data}\n\n"
            try:
                parsed = json.loads(data)
            except (ValueError, TypeError):
                parsed = {}
            if parsed.get("type") in _TERMINAL_EVENTS:
                break
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.get("/{upload_id}/events", operation_id="uploads_events")
async def stream_upload_events(
    upload_id: uuid.UUID,
    request: Request,
    db: DBSession,
    token: str = Query(..., description="Access JWT (EventSource cannot set headers)"),
):
    from fastapi.responses import StreamingResponse

    user = await _user_from_query_token(token, db)

    upload = await db.scalar(select(Upload).where(Upload.id == upload_id))
    if upload is None:
        raise NotFoundError("Upload")
    if upload.user_id != user.id:
        raise ForbiddenError("Not your upload")

    return StreamingResponse(
        _event_stream(request, channel_for_upload(upload_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx proxy buffering
        },
    )
