import enum
import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class QuestionSetStatus(str, enum.Enum):
    generating = "generating"             # AI worker in flight
    generation_failed = "generation_failed"  # AI worker errored
    draft = "draft"
    published = "published"
    rejected = "rejected"


class QuestionDifficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionSet(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "question_sets"
    __table_args__ = (
        Index("ix_question_sets_upload_id", "upload_id"),
        Index("ix_question_sets_subject_id", "subject_id"),
        Index("ix_question_sets_status", "status"),
    )

    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[QuestionSetStatus] = mapped_column(
        Enum(QuestionSetStatus, name="question_set_status"),
        nullable=False,
        default=QuestionSetStatus.draft,
        server_default="draft",
    )
    ai_model: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generation_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Question(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_question_set_id", "question_set_id"),)

    question_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("question_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty, name="question_difficulty"),
        nullable=False,
        default=QuestionDifficulty.medium,
        server_default="medium",
    )
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class QuestionChoice(UUIDMixin, Base):
    __tablename__ = "question_choices"
    __table_args__ = (Index("ix_question_choices_question_id", "question_id"),)

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
