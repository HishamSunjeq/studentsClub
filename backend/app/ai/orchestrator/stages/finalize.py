"""Stage 7: persist judged + deduped questions and flip the QS to draft (Phase 4)."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.ai.orchestrator.schemas import JudgedQuestion
from app.core.database import AsyncSessionLocal
from app.models.question import (
    Question,
    QuestionChoice,
    QuestionSet,
    QuestionSetStatus,
)

logger = logging.getLogger(__name__)


async def finalize_question_set(
    *,
    question_set_id: uuid.UUID,
    judged: list[JudgedQuestion],
    extraction_model: str,
    prompt_version_id: uuid.UUID | None,
    total_tokens_used: int,
) -> int:
    """Bulk-insert questions + choices and flip QS status. Returns the
    number of rows actually inserted (auto_rejected included so the
    review UI can show what was dropped and why).
    """
    inserted = 0
    async with AsyncSessionLocal() as db:
        async with db.begin():
            qs_res = await db.execute(
                select(QuestionSet).where(QuestionSet.id == question_set_id)
            )
            qs = qs_res.scalar_one()

            for pos, j in enumerate(judged):
                q = Question(
                    question_set_id=qs.id,
                    text=j.question.text,
                    explanation=j.question.explanation,
                    difficulty=j.question.difficulty,
                    source_excerpt=j.question.source_excerpt,
                    is_active=not j.auto_rejected,
                    position=pos,
                    quality_score=Decimal(str(round(j.quality_score, 1))),
                    source_chunk_ids=list(j.question.source_chunk_ids),
                    prompt_version_id=prompt_version_id,
                    auto_rejected=j.auto_rejected,
                )
                db.add(q)
                await db.flush()
                inserted += 1
                for choice_pos, c in enumerate(j.question.choices):
                    db.add(
                        QuestionChoice(
                            question_id=q.id,
                            text=c.text,
                            is_correct=c.is_correct,
                            position=choice_pos,
                        )
                    )

            qs.status = QuestionSetStatus.draft
            qs.ai_model = extraction_model
            qs.tokens_used = total_tokens_used
            qs.generation_error = None

    return inserted
