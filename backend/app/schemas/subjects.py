import uuid
from datetime import datetime

from pydantic import BaseModel


class SubjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    college: str
    academic_year: int
    description: str | None
    created_at: datetime
    member_count: int = 0
    published_question_set_count: int = 0
    question_count: int = 0

    model_config = {"from_attributes": True}


class SubjectListResponse(BaseModel):
    items: list[SubjectResponse]
    total: int
    page: int
    size: int
    pages: int


class EnrollmentResponse(BaseModel):
    subject_id: uuid.UUID
    enrolled_at: datetime

    model_config = {"from_attributes": True}


class SubjectMemberResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    college: str
    academic_year: int
    enrolled_at: datetime


class SubjectMemberListResponse(BaseModel):
    items: list[SubjectMemberResponse]
    total: int
    page: int
    size: int
    pages: int


class SubjectContributorResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    question_set_count: int


class SubjectPublishedSetResponse(BaseModel):
    id: uuid.UUID
    title: str
    question_count: int
    created_at: datetime


class SubjectPublishedSetListResponse(BaseModel):
    items: list[SubjectPublishedSetResponse]
    total: int
    page: int
    size: int
    pages: int
