"""Anthropic provider.

Phase 2: accepts an explicit `api_key`, `model`, and `system_prompt` so
the factory can wire it from the DB-backed credential store, model
registry, and prompt registry. All three fall back to env defaults
when omitted, preserving the legacy single-key dev setup.
"""

from __future__ import annotations

import json
from typing import Literal

import anthropic

from app.ai.base import AIProvider, ChoiceDraft, ExtractionResult, QuestionDraft
from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT
from app.core.config import settings


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self._system_prompt = system_prompt or EXTRACTION_SYSTEM_PROMPT

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult:
        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        user_content = "\n\n---\n\n".join(chunks)
        if target_count:
            user_content = f"Generate exactly {target_count} questions.\n\n{user_content}"

        response = await client.beta.prompt_caching.messages.create(
            model=self.model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": self._system_prompt,
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
