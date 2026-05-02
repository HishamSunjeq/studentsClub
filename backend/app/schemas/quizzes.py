from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.question import QuestionDifficulty
from app.models.quiz import QuizSessionStatus


class QuizChoiceResponse(BaseModel):
    """Choice without is_correct — server hides the answer until /answer is called."""
    id: UUID
    text: str
    position: int

    model_config = {"from_attributes": True}


class QuizQuestionResponse(BaseModel):
    id: UUID
    text: str
    difficulty: QuestionDifficulty
    position: int
    choices: list[QuizChoiceResponse]


class QuizStartRequest(BaseModel):
    subject_id: UUID
    count: int = Field(default=10, ge=1, le=50)


class QuizSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    subject_id: UUID
    status: QuizSessionStatus
    total_questions: int
    score: int
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizSessionWithQuestionsResponse(QuizSessionResponse):
    questions: list[QuizQuestionResponse]
    answered_question_ids: list[UUID] = []


class QuizAnswerRequest(BaseModel):
    question_id: UUID
    choice_id: UUID


class QuizAnswerResponse(BaseModel):
    is_correct: bool
    correct_choice_id: UUID
    explanation: str | None
    answered_count: int
    score: int


class QuizSessionListResponse(BaseModel):
    items: list[QuizSessionResponse]
    total: int
    page: int
    size: int
    pages: int
