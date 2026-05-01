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
