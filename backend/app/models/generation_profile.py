"""Per-subject generation profiles (Phase 2).

A profile bundles: prompt names, model ids (from `ai_models`),
credential aliases (from `ai_credentials`), tuning knobs (judge
threshold, dedup threshold, rerank k/n, hybrid alpha), and difficulty
mix. Subject-scoped if `subject_id` is set; global default otherwise.

Only one row may have `is_default=true` per (subject_id) — partial
unique index in the migration enforces this.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class GenerationProfile(UUIDMixin, Base):
    __tablename__ = "generation_profiles"
    __table_args__ = (
        Index("ix_generation_profiles_subject_id", "subject_id"),
    )

    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)

    prompt_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="extraction.system")
    judge_prompt_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="judge.rubric")

    extraction_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    judge_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    embedding_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    rerank_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="SET NULL"),
        nullable=True,
    )

    credential_alias_extraction: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_alias_judge: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_alias_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_alias_rerank: Mapped[str | None] = mapped_column(Text, nullable=True)

    target_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20, server_default="20"
    )
    difficulty_mix: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default='{"easy": 0.3, "medium": 0.5, "hard": 0.2}',
    )

    judge_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 1), nullable=False, default=Decimal("6.0"), server_default="6.0"
    )
    dedup_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.92"), server_default="0.92"
    )

    top_k_retrieval: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, server_default="50"
    )
    top_n_rerank: Mapped[int] = mapped_column(
        Integer, nullable=False, default=8, server_default="8"
    )
    hybrid_alpha: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.5"), server_default="0.5"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
