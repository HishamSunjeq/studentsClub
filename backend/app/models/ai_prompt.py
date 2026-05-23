"""DB-backed prompt registry (Phase 2).

One row per *version* of a prompt. The active version is the one with
`is_active=true` for a given `name`. A partial unique index in the
migration enforces "at most one active per name". Activation is a
two-step operation in the API: deactivate all current actives, then
flip the chosen version to active — wrapped in a single transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AIPrompt(UUIDMixin, Base):
    __tablename__ = "ai_prompts"
    __table_args__ = (
        Index("ix_ai_prompts_name", "name"),
        Index("ix_ai_prompts_name_version", "name", "version", unique=True),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="system")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_hint: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
