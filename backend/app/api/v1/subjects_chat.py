"""Subject Q&A chat endpoints (Phase 7).

Enrolled members (or admins) can open chat sessions scoped to a subject and
ask questions answered from that subject's hybrid RAG index. Each assistant
turn persists its grounding citations so the UI can show source excerpts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.ai.rag.qa import answer_subject_question
from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.chat import ChatMessage, ChatSession
from app.models.subject import Enrollment, Subject
from app.models.user import User, UserRole
from app.schemas.chat import (
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSendRequest,
    ChatSendResponse,
    ChatSessionCreateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
)

router = APIRouter()


async def _require_member(db: DBSession, user: User, subject_id: uuid.UUID) -> Subject:
    subject = await db.get(Subject, subject_id)
    if subject is None:
        raise NotFoundError("Subject")
    if user.role == UserRole.admin:
        return subject
    enrolled = await db.scalar(
        select(Enrollment.id).where(
            Enrollment.user_id == user.id,
            Enrollment.subject_id == subject_id,
        )
    )
    if enrolled is None:
        raise ForbiddenError("You must be enrolled in this subject to use chat")
    return subject


async def _owned_session(
    db: DBSession, user: User, subject_id: uuid.UUID, session_id: uuid.UUID
) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None or session.subject_id != subject_id:
        raise NotFoundError("Chat session")
    if session.user_id != user.id:
        raise ForbiddenError("Not your chat session")
    return session


@router.get(
    "/{subject_id}/chat/sessions",
    response_model=ChatSessionListResponse,
    operation_id="subject_chat_sessions_list",
)
async def list_sessions(
    subject_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> ChatSessionListResponse:
    await _require_member(db, current_user, subject_id)
    rows = await db.scalars(
        select(ChatSession)
        .where(
            ChatSession.subject_id == subject_id,
            ChatSession.user_id == current_user.id,
        )
        .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
    )
    return ChatSessionListResponse(
        items=[ChatSessionResponse.model_validate(s) for s in rows.all()]
    )


@router.post(
    "/{subject_id}/chat/sessions",
    response_model=ChatSessionResponse,
    operation_id="subject_chat_sessions_create",
)
async def create_session(
    subject_id: uuid.UUID,
    body: ChatSessionCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ChatSessionResponse:
    await _require_member(db, current_user, subject_id)
    session = ChatSession(
        subject_id=subject_id,
        user_id=current_user.id,
        title=body.title or "New chat",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionResponse.model_validate(session)


@router.get(
    "/{subject_id}/chat/sessions/{session_id}/messages",
    response_model=ChatMessageListResponse,
    operation_id="subject_chat_messages_list",
)
async def list_messages(
    subject_id: uuid.UUID,
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ChatMessageListResponse:
    await _require_member(db, current_user, subject_id)
    await _owned_session(db, current_user, subject_id, session_id)
    rows = await db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return ChatMessageListResponse(
        items=[ChatMessageResponse.model_validate(m) for m in rows.all()]
    )


@router.post(
    "/{subject_id}/chat/sessions/{session_id}/messages",
    response_model=ChatSendResponse,
    operation_id="subject_chat_send",
)
async def send_message(
    subject_id: uuid.UUID,
    session_id: uuid.UUID,
    body: ChatSendRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ChatSendResponse:
    await _require_member(db, current_user, subject_id)
    session = await _owned_session(db, current_user, subject_id, session_id)

    # Prior turns for conversational context.
    history_rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
    ).all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_msg = ChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)

    result = await answer_subject_question(
        db,
        subject_id=subject_id,
        query=body.content,
        history=history,
        user_id=current_user.id,
    )

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result.answer,
        citations=result.citations_json(),
        tokens=result.tokens,
        model=result.model,
    )
    db.add(assistant_msg)

    # First user turn names the session.
    if not history:
        session.title = body.content[:80]
    session.last_message_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    return ChatSendResponse(
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
    )
