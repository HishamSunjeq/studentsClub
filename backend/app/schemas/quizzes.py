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
    difficulties: list[QuestionDifficulty] | None = None


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


class QuizQuestionResult(BaseModel):
    """Per-question breakdown shown on the result page."""

    question_id: UUID
    text: str
    difficulty: QuestionDifficulty
    explanation: str | None
    selected_choice_id: UUID | None
    correct_choice_id: UUID
    is_correct: bool
    choices: list["QuizResultChoice"]


class QuizResultChoice(BaseModel):
    id: UUID
    text: str
    position: int

    model_config = {"from_attributes": True}


class QuizDifficultyBreakdown(BaseModel):
    difficulty: QuestionDifficulty
    correct: int
    total: int


class QuizResultResponse(BaseModel):
    session_id: UUID
    subject_id: UUID
    status: QuizSessionStatus
    score: int
    total: int
    accuracy: float  # 0..1
    correct_count: int
    incorrect_count: int
    skipped_count: int
    completed_at: datetime | None
    breakdown_by_difficulty: list[QuizDifficultyBreakdown]
    # Accuracy delta vs prior completed quiz in the same subject (0..1 scale, can be negative).
    trend: float | None
    questions: list[QuizQuestionResult]
