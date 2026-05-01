from typing import Literal

from app.ai.base import AIProvider, ExtractionResult


class OpenAIProvider:
    """OpenAI provider — implemented in Phase 4."""

    name = "openai"

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError("OpenAIProvider will be implemented in Phase 4")


_: AIProvider = OpenAIProvider()
