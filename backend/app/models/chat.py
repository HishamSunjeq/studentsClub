"""Subject Q&A chat (Phase 7).

A `ChatSession` is one conversation thread scoped to a subject and owned by a
user. `ChatMessage` rows are the turns; assistant turns carry `citations`
(resolved chunk references) so the UI can show grounded "based on" excerpts.
Vectors live in Qdrant — these tables only persist the conversation itself.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

ChatRole = Enum("user", "assistant", name="chat_role", create_type=False)


class ChatSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, default="New chat")
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class ChatMessage(UUIDMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(ChatRole, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # List of {chunk_id, upload_id, section_title, text} the answer was grounded on.
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=None)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
