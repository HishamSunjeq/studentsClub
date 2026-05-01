from typing import Literal

from app.ai.base import AIProvider, ExtractionResult


class AnthropicProvider:
    """Anthropic Claude provider — implemented in Phase 4."""

    name = "anthropic"

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError("AnthropicProvider will be implemented in Phase 4")


_: AIProvider = AnthropicProvider()
