import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UploadStatus(str, enum.Enum):
    pending = "pending"          # presigned URL issued, awaiting client PUT
    uploaded = "uploaded"        # client confirmed PUT, file is in S3
    extracting = "extracting"    # text extraction worker running
    ready = "ready"              # text extracted, available for generation
    failed = "failed"            # extraction failed


ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)


class Upload(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "uploads"
    __table_args__ = (
        Index("ix_uploads_user_id", "user_id"),
        Index("ix_uploads_subject_id", "subject_id"),
        Index("ix_uploads_status", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status"),
        nullable=False,
        default=UploadStatus.pending,
        server_default="pending",
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_backend: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
