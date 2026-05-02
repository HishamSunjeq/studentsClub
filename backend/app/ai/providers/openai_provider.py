import json
from typing import Literal

from openai import AsyncOpenAI

from app.ai.base import AIProvider, ChoiceDraft, ExtractionResult, QuestionDraft
from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT
from app.core.config import settings


class OpenAIProvider:
    name = "openai"

    async def extract_questions(
        self,
        chunks: list[str],
        source_type: Literal["study_material", "exam_paper"],
        target_count: int | None = None,
    ) -> ExtractionResult:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        user_content = "\n\n---\n\n".join(chunks)
        if target_count:
            user_content = f"Generate exactly {target_count} questions.\n\n{user_content}"

        response = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = response.choices[0].message.content or ""
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

        usage = response.usage
        return ExtractionResult(
            questions=questions,
            tokens_input=usage.prompt_tokens if usage else 0,
            tokens_output=usage.completion_tokens if usage else 0,
            model=response.model,
        )


_: AIProvider = OpenAIProvider()
