from typing import Literal, Protocol

from pydantic import BaseModel


class ChoiceDraft(BaseModel):
    text: str
    is_correct: bool


class QuestionDraft(BaseModel):
    text: str
    choices: list[ChoiceDraft]
    explanation: str | None = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_excerpt: str | None = None


class ExtractionResult(BaseModel):
    questions: list[QuestionDraft]
    tokens_input: int = 0
    tokens_output: int = 0
    model: str


class AIProvider(Protocol):
    name: str

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult: ...
