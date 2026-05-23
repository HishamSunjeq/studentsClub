"""Model registry (Phase 2).

DB-backed catalog of LLM/embedding/rerank models. The orchestrator and
providers read context window, pricing, and capability flags from here
instead of hardcoding strings. Seeded by migration 0010.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ModelKind(str, enum.Enum):
    extraction = "extraction"
    judge = "judge"
    embedding = "embedding"
    rerank = "rerank"
    chat = "chat"
    vision = "vision"


class AIModel(UUIDMixin, Base):
    __tablename__ = "ai_models"
    __table_args__ = (
        Index("ix_ai_models_provider", "provider"),
        Index("ix_ai_models_kind", "kind"),
        Index("ix_ai_models_provider_model_id", "provider", "model_id", unique=True),
    )

    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[ModelKind] = mapped_column(
        Enum(ModelKind, name="ai_model_kind"), nullable=False
    )

    context_window: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    input_cost_per_mtoken: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0"), server_default="0"
    )
    output_cost_per_mtoken: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0"), server_default="0"
    )

    supports_streaming: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    supports_json_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    supports_prompt_cache: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
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
