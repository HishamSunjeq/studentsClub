import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    college: str
    academic_year: int
    role: UserRole
    email_verified_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserStatsResponse(BaseModel):
    """Aggregate stats surfaced on the dashboard hero + bento."""

    streak_days: int
    xp_total: int
    weekly_goal: int
    weekly_progress: int
    accuracy_avg: float  # 0..1
    correct_count: int
    total_attempts: int
    drafts_pending_review_count: int
    published_question_count: int


class ContinueSessionResponse(BaseModel):
    session_id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: str
    subject_code: str
    total_questions: int
    answered_questions: int
    progress: float  # 0..1
    started_at: datetime


class FeedItemResponse(BaseModel):
    question_set_id: uuid.UUID
    title: str
    subject_id: uuid.UUID
    subject_name: str
    subject_code: str
    author_id: uuid.UUID
    author_name: str
    question_count: int
    published_at: datetime


class FeedListResponse(BaseModel):
    items: list[FeedItemResponse]
    total: int
    page: int
    size: int
    pages: int


class RecommendedSubjectItem(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    college: str
    academic_year: int
    description: str | None

    model_config = {"from_attributes": True}
