import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class QuizSessionStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class QuizSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = (
        Index("ix_quiz_sessions_user_id", "user_id"),
        Index("ix_quiz_sessions_subject_id", "subject_id"),
        Index("ix_quiz_sessions_status", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[QuizSessionStatus] = mapped_column(
        Enum(QuizSessionStatus, name="quiz_session_status"),
        nullable=False,
        default=QuizSessionStatus.in_progress,
        server_default="in_progress",
    )
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class QuizSessionQuestion(UUIDMixin, Base):
    """The N questions picked for a session at start time, in order."""
    __tablename__ = "quiz_session_questions"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_qsq_session_position"),
        UniqueConstraint("session_id", "question_id", name="uq_qsq_session_question"),
        Index("ix_quiz_session_questions_session_id", "session_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class QuizAttempt(UUIDMixin, Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_session_id", "session_id"),
        Index("ix_quiz_attempts_question_id", "question_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_choice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("question_choices.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
