from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.question import QuestionDifficulty, QuestionSetStatus


class QuestionChoiceResponse(BaseModel):
    id: UUID
    text: str
    is_correct: bool
    position: int

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    id: UUID
    question_set_id: UUID
    text: str
    explanation: str | None
    difficulty: QuestionDifficulty
    source_excerpt: str | None
    is_active: bool
    position: int
    choices: list[QuestionChoiceResponse]

    model_config = {"from_attributes": True}


class QuestionSetResponse(BaseModel):
    id: UUID
    upload_id: UUID
    subject_id: UUID | None
    created_by: UUID
    title: str
    status: QuestionSetStatus
    ai_model: str
    tokens_used: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionSetWithQuestionsResponse(QuestionSetResponse):
    questions: list[QuestionResponse]


class QuestionSetListResponse(BaseModel):
    items: list[QuestionSetResponse]
    total: int
    page: int
    size: int
    pages: int


class QuestionSetUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class QuestionChoiceUpdate(BaseModel):
    text: str = Field(..., min_length=1)
    is_correct: bool


class QuestionUpdateRequest(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    explanation: str | None = None
    difficulty: QuestionDifficulty | None = None
    choices: list[QuestionChoiceUpdate] | None = None

    @model_validator(mode="after")
    def validate_choices(self) -> "QuestionUpdateRequest":
        if self.choices is not None:
            if len(self.choices) != 4:
                raise ValueError("must provide exactly 4 choices")
            correct_count = sum(1 for c in self.choices if c.is_correct)
            if correct_count != 1:
                raise ValueError("exactly one choice must be marked correct")
        return self
