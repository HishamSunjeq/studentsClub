"""Per-user UI settings + the in-app notifications inbox."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ThemePreference(str, enum.Enum):
    system = "system"
    light = "light"
    dark = "dark"


class DensityPreference(str, enum.Enum):
    comfortable = "comfortable"
    compact = "compact"


class NotificationType(str, enum.Enum):
    draft_ready = "draft_ready"
    question_set_published = "question_set_published"
    question_set_voted = "question_set_voted"
    new_material_in_subject = "new_material_in_subject"


class UserSettings(UUIDMixin, TimestampMixin, Base):
    """Per-user UI + notification preferences. Created lazily on first read."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    theme: Mapped[ThemePreference] = mapped_column(
        Enum(ThemePreference, name="theme_preference"),
        nullable=False,
        default=ThemePreference.system,
        server_default="system",
    )
    accent_color: Mapped[str] = mapped_column(
        Text, nullable=False, default="indigo", server_default="indigo"
    )
    density: Mapped[DensityPreference] = mapped_column(
        Enum(DensityPreference, name="density_preference"),
        nullable=False,
        default=DensityPreference.comfortable,
        server_default="comfortable",
    )
    language: Mapped[str] = mapped_column(
        Text, nullable=False, default="en", server_default="en"
    )
    # Map of {notification_type: enabled_bool}; defaults to all-on when missing.
    notification_prefs: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )


class Notification(UUIDMixin, TimestampMixin, Base):
    """In-app notification — backs the bell drawer in the top bar."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_read_at", "read_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form payload — e.g. {"subject_id": "...", "question_set_id": "..."} for click-through.
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
