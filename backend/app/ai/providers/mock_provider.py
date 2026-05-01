from typing import Literal

from app.ai.base import AIProvider, ChoiceDraft, ExtractionResult, QuestionDraft


class MockProvider:
    """Deterministic provider for tests — never calls any external API."""

    name = "mock"

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult:
        count = min(target_count or 3, len(chunks) + 1)
        questions = [
            QuestionDraft(
                text=f"Mock question {i + 1} based on: {chunks[0][:40] if chunks else 'content'}?",
                choices=[
                    ChoiceDraft(text="Correct answer", is_correct=True),
                    ChoiceDraft(text="Wrong answer A", is_correct=False),
                    ChoiceDraft(text="Wrong answer B", is_correct=False),
                    ChoiceDraft(text="Wrong answer C", is_correct=False),
                ],
                explanation="Mock explanation for testing.",
                difficulty="easy",
                source_excerpt=chunks[0][:100] if chunks else None,
            )
            for i in range(count)
        ]
        return ExtractionResult(questions=questions, model="mock")


# Satisfy AIProvider Protocol
_: AIProvider = MockProvider()
