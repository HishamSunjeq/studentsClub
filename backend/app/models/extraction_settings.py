"""Global document-extraction configuration (Phase 9).

A single-row table holding admin-tunable extraction knobs: which backend
to use (`unstructured` vs the legacy pdfplumber/python-docx/tesseract path),
the unstructured partition strategy, OCR languages, and table extraction.
Editable from the admin Extraction page; read by `process_upload`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ExtractionSettings(UUIDMixin, Base):
    __tablename__ = "extraction_settings"

    # "unstructured" | "legacy"
    backend: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="unstructured"
    )
    # unstructured partition strategy: "auto" | "hi_res" | "ocr_only" | "fast"
    strategy: Mapped[str] = mapped_column(Text, nullable=False, server_default="auto")
    # tesseract language codes, e.g. {eng, ara}
    ocr_languages: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{eng,ara}"
    )
    extract_tables: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    hi_res_model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_characters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
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
