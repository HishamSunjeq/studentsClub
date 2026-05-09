"""AI question-generation worker.

User-triggered: invoked from `uploads_service.generate_questions` after the user
configures count/difficulty/etc on a `ready` upload. The QuestionSet row is
inserted in `generating` status by the service before this task runs; the worker
fills in questions/choices and transitions the row to `draft` (or `generation_failed`).
"""

import asyncio
import uuid
from typing import Any

from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.tasks.extract_questions.run", bind=True, max_retries=3
)
def run(self, question_set_id: str, settings: dict[str, Any]) -> dict:  # type: ignore[return]
    try:
        return asyncio.run(_async_run(question_set_id, settings))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(question_set_id, str(exc)))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _async_run(question_set_id: str, settings: dict[str, Any]) -> dict:
    from sqlalchemy import select

    from app.ai.factory import get_provider
    from app.ai.parsers import chunk_text
    from app.core.database import AsyncSessionLocal
    from app.models.question import (
        Question,
        QuestionChoice,
        QuestionSet,
        QuestionSetStatus,
    )
    from app.models.upload import Upload

    qs_uuid = uuid.UUID(question_set_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(QuestionSet).where(QuestionSet.id == qs_uuid))
        qs = result.scalar_one_or_none()
        if qs is None:
            raise ValueError(f"QuestionSet {question_set_id} not found")
        upload_result = await db.execute(
            select(Upload).where(Upload.id == qs.upload_id)
        )
        upload = upload_result.scalar_one()
        if not upload.extracted_text:
            raise ValueError(
                f"Upload {upload.id} has no extracted_text; cannot generate"
            )
        text = upload.extracted_text

    chunks = chunk_text(text)
    provider = get_provider()
    target_count = int(settings.get("count") or 0) or None
    result_obj = await provider.extract_questions(
        chunks, source_type="study_material", target_count=target_count
    )

    async with AsyncSessionLocal() as db:
        async with db.begin():
            qs_result = await db.execute(
                select(QuestionSet).where(QuestionSet.id == qs_uuid)
            )
            qs = qs_result.scalar_one()
            qs.status = QuestionSetStatus.draft
            qs.ai_model = result_obj.model
            qs.tokens_used = result_obj.tokens_input + result_obj.tokens_output
            qs.generation_error = None

            for pos, q_draft in enumerate(result_obj.questions):
                question = Question(
                    question_set_id=qs.id,
                    text=q_draft.text,
                    explanation=q_draft.explanation,
                    difficulty=q_draft.difficulty,
                    source_excerpt=q_draft.source_excerpt,
                    is_active=True,
                    position=pos,
                )
                db.add(question)
                await db.flush()

                for choice_pos, c_draft in enumerate(q_draft.choices):
                    db.add(
                        QuestionChoice(
                            question_id=question.id,
                            text=c_draft.text,
                            is_correct=c_draft.is_correct,
                            position=choice_pos,
                        )
                    )

    return {
        "question_set_id": question_set_id,
        "questions_created": len(result_obj.questions),
        "model": result_obj.model,
    }


async def _mark_failed(question_set_id: str, message: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.question import QuestionSet, QuestionSetStatus

    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                select(QuestionSet).where(QuestionSet.id == uuid.UUID(question_set_id))
            )
            qs = result.scalar_one_or_none()
            if qs is None:
                return
            qs.status = QuestionSetStatus.generation_failed
            qs.generation_error = message[:2000]
