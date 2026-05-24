"""Encrypted provider credentials (Phase 2).

`key_encrypted` is Fernet ciphertext of the raw API key. The plaintext
key is *never* exposed via the API — responses include only
`key_last4`. Encryption / decryption happens in `app.ai.credentials`.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, LargeBinary, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class CredentialProvider(str, enum.Enum):
    anthropic = "anthropic"
    openai = "openai"
    cohere = "cohere"
    voyage = "voyage"
    qdrant = "qdrant"


class CredentialScope(str, enum.Enum):
    global_ = "global"
    subject = "subject"


class AICredential(UUIDMixin, Base):
    __tablename__ = "ai_credentials"
    __table_args__ = (
        Index("ix_ai_credentials_provider", "provider"),
        Index("ix_ai_credentials_alias", "alias", unique=True),
    )

    alias: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[CredentialProvider] = mapped_column(
        Enum(CredentialProvider, name="ai_credential_provider"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_last4: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    scope: Mapped[CredentialScope] = mapped_column(
        Enum(
            CredentialScope,
            name="ai_credential_scope",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CredentialScope.global_,
        server_default="global",
    )
    scope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    monthly_budget_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
