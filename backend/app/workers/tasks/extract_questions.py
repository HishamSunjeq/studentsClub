import asyncio
import uuid

from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.tasks.extract_questions.run", bind=True, max_retries=3
)
def run(  # type: ignore[return]
    self,
    upload_id: str,
    chunks: list[str],
    user_id: str,
    subject_id: str | None,
) -> dict:
    try:
        return asyncio.run(_async_run(upload_id, chunks, user_id, subject_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _async_run(
    upload_id: str,
    chunks: list[str],
    user_id: str,
    subject_id: str | None,
) -> dict:
    from app.ai.factory import get_provider
    from app.core.database import AsyncSessionLocal
    from app.models.question import (
        Question,
        QuestionChoice,
        QuestionSet,
        QuestionSetStatus,
    )

    provider = get_provider()
    result = await provider.extract_questions(chunks, source_type="study_material")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            qs = QuestionSet(
                upload_id=uuid.UUID(upload_id),
                subject_id=uuid.UUID(subject_id) if subject_id else None,
                created_by=uuid.UUID(user_id),
                title=f"AI Draft — upload {upload_id[:8]}",
                status=QuestionSetStatus.draft,
                ai_model=result.model,
                tokens_used=result.tokens_input + result.tokens_output,
            )
            db.add(qs)
            await db.flush()

            for pos, q_draft in enumerate(result.questions):
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
        "question_set_id": str(qs.id),
        "questions_created": len(result.questions),
        "model": result.model,
    }
