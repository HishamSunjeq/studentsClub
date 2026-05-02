import json
from typing import Literal

import anthropic

from app.ai.base import AIProvider, ChoiceDraft, ExtractionResult, QuestionDraft
from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT
from app.core.config import settings


class AnthropicProvider:
    name = "anthropic"

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        user_content = "\n\n---\n\n".join(chunks)
        if target_count:
            user_content = f"Generate exactly {target_count} questions.\n\n{user_content}"

        # System prompt cached — constant across all extraction calls.
        response = await client.beta.prompt_caching.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": EXTRACTION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text
        data: dict = json.loads(raw)
        questions = [
            QuestionDraft(
                text=q["text"],
                choices=[ChoiceDraft(**c) for c in q["choices"]],
                explanation=q.get("explanation"),
                difficulty=q.get("difficulty", "medium"),
                source_excerpt=q.get("source_excerpt"),
            )
            for q in data["questions"]
        ]

        return ExtractionResult(
            questions=questions,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model,
        )


_: AIProvider = AnthropicProvider()
