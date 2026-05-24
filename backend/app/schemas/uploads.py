from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.question import QuestionSetStatus
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
    extracted_at: datetime | None
    extraction_error: str | None
    extraction_backend: str | None = None
    extraction_strategy: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadQuestionSetSummary(BaseModel):
    id: UUID
    title: str
    status: QuestionSetStatus
    created_at: datetime
    question_count: int
    generation_settings: dict[str, Any]
    generation_error: str | None

    model_config = {"from_attributes": True}


class UploadDetailResponse(UploadResponse):
    """Same as UploadResponse plus a preview of the extracted text and a list of
    question sets generated from this upload.
    """

    extracted_text_preview: str | None = None
    question_sets: list[UploadQuestionSetSummary] = []


class UploadListResponse(BaseModel):
    items: list[UploadResponse]
    total: int
    page: int
    size: int


class UploadUpdateRequest(BaseModel):
    subject_id: UUID | None = None


class PreviewUrlResponse(BaseModel):
    url: str
    expires_in: int


# ---------- Generation ----------


class DifficultyMix(BaseModel):
    easy: int = Field(ge=0, le=100, default=30)
    medium: int = Field(ge=0, le=100, default=50)
    hard: int = Field(ge=0, le=100, default=20)


class GenerateRequest(BaseModel):
    count: int = Field(ge=1, le=50, default=10)
    difficulty_mix: DifficultyMix = Field(default_factory=DifficultyMix)
    question_types: list[str] = Field(default_factory=lambda: ["mcq"])
    language: str = "en"
    # Admin-only per-run overrides (validated in the service layer).
    extraction_model_id: UUID | None = None
    profile_id: UUID | None = None

    @field_validator("difficulty_mix")
    @classmethod
    def mix_sums_to_100(cls, v: DifficultyMix) -> DifficultyMix:
        total = v.easy + v.medium + v.hard
        if total != 100:
            raise ValueError(f"difficulty_mix must sum to 100, got {total}")
        return v


class GenerationModelOption(BaseModel):
    id: UUID
    display_name: str
    model_id: str
    provider: str


class GenerationProfileOption(BaseModel):
    id: UUID
    name: str
    subject_id: UUID | None = None
    is_default: bool


class GenerationDefaultsResponse(BaseModel):
    """What *would* run for this upload, plus (admins only) the selectable
    active extraction models and profiles for a per-run override.
    """

    profile_id: UUID | None = None
    profile_name: str
    extraction_provider: str
    extraction_model: str
    extraction_model_display: str
    is_admin: bool
    models: list[GenerationModelOption] = Field(default_factory=list)
    profiles: list[GenerationProfileOption] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    """Returned immediately when generation is queued — the QuestionSet is in
    `generating` status. Poll `GET /question-sets/{id}` (or the upload detail)
    for completion.
    """

    question_set_id: UUID
    status: QuestionSetStatus
