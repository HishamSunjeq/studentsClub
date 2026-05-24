"""SSE stream for subject chat (Phase 7 / 8).

`GET /api/v1/subjects/{subject_id}/chat/sessions/{session_id}/events?token=...`
subscribes to the Redis channel `subject:chat:{session_id}` and streams the
assistant's tokens + a terminal `done` event with grounded citations.

Same JWT-via-query-param pattern as uploads_events.py — EventSource cannot
set headers.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

import jwt
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.ai.events import channel_for_chat
from app.ai.redis_client import get_redis
from app.api.deps import DBSession
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_token
from app.models.chat import ChatSession
from app.models.subject import Enrollment
from app.models.user import User, UserRole

router = APIRouter()

_HEARTBEAT_SECONDS = 15
_TERMINAL_EVENTS = {"done", "error"}


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
    return f"data: {json.dumps(event, default=str)}\n\n"


async def _event_stream(request: Request, channel: str) -> AsyncIterator[str]:
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        yield _sse({"type": "stream.open"})
        while True:
            if await request.is_disconnected():
                break
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=_HEARTBEAT_SECONDS
            )
            if message is None:
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


@router.get(
    "/{subject_id}/chat/sessions/{session_id}/events",
    operation_id="subject_chat_events",
)
async def stream_chat_events(
    subject_id: uuid.UUID,
    session_id: uuid.UUID,
    request: Request,
    db: DBSession,
    token: str = Query(..., description="Access JWT (EventSource cannot set headers)"),
):
    user = await _user_from_query_token(token, db)

    session = await db.get(ChatSession, session_id)
    if session is None or session.subject_id != subject_id:
        raise NotFoundError("Chat session")
    if session.user_id != user.id:
        raise ForbiddenError("Not your chat session")

    if user.role != UserRole.admin:
        enrolled = await db.scalar(
            select(Enrollment.id).where(
                Enrollment.user_id == user.id,
                Enrollment.subject_id == subject_id,
            )
        )
        if enrolled is None:
            raise ForbiddenError("You must be enrolled in this subject to use chat")

    return StreamingResponse(
        _event_stream(request, channel_for_chat(session_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
