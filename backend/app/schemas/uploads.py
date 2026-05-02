from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.upload import ALLOWED_CONTENT_TYPES, UploadStatus


class UploadCreateRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    subject_id: UUID | None = None

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"content_type not allowed: {v}")
        return v


class PresignResponse(BaseModel):
    upload_id: UUID
    presigned_url: str
    s3_key: str


class UploadResponse(BaseModel):
    id: UUID
    user_id: UUID
    subject_id: UUID | None
    original_filename: str
    content_type: str
    size_bytes: int
    s3_key: str
    status: UploadStatus
    finalized_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
