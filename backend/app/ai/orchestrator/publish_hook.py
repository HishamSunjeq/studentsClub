"""Publish hook — upsert accepted questions into the Qdrant `questions` collection.

Called from `POST /question-sets/{id}/publish`. Each accepted question
gets embedded (text-embedding-3-small) and upserted as a single dense
point keyed by `question_id`. Soft-deletes / rejections remove the
point so dedup against the live bank stays accurate.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.ai.rag import EMBEDDING_VERSION
from app.ai.rag.embedder.factory import get_embedder
from app.ai.rag.index import delete_question, upsert_question
from app.models.question import Question
from app.models.question_embedding_meta import QuestionEmbeddingMeta

logger = logging.getLogger(__name__)


async def upsert_accepted_questions(
    db: AsyncSession,
    *,
    question_set_id: uuid.UUID,
    subject_id: uuid.UUID | None,
    published: bool = True,
) -> int:
    """Embed + upsert every active question in the set. Returns count."""
    res = await db.execute(
        select(Question).where(
            Question.question_set_id == question_set_id,
            Question.is_active.is_(True),
            Question.auto_rejected.is_(False),
        )
    )
    questions = list(res.scalars().all())
    if not questions:
        return 0

    try:
        embedder = await get_embedder()
        vectors = await embedder.embed([q.text for q in questions])
    except Exception:
        logger.exception("publish_hook: embedding failed; skipping Qdrant upsert")
        return 0

    upserted = 0
    for q, vec in zip(questions, vectors):
        try:
            await upsert_question(
                question_id=q.id,
                subject_id=subject_id,
                dense=vec,
                published=published,
                embedding_model=embedder.name,
            )
            await db.execute(
                pg_insert(QuestionEmbeddingMeta)
                .values(
                    question_id=q.id,
                    subject_id=subject_id,
                    embedding_model=embedder.name,
                    embedding_version=EMBEDDING_VERSION,
                    indexed_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_update(
                    index_elements=["question_id"],
                    set_={
                        "subject_id": subject_id,
                        "embedding_model": embedder.name,
                        "embedding_version": EMBEDDING_VERSION,
                        "indexed_at": datetime.now(timezone.utc),
                    },
                )
            )
            upserted += 1
        except Exception:
            logger.exception("publish_hook: failed to upsert question=%s", q.id)
    return upserted


async def remove_questions_from_bank(
    db: AsyncSession, *, question_ids: list[uuid.UUID]
) -> None:
    """Remove published questions from Qdrant + clear their embedding meta."""
    for qid in question_ids:
        try:
            await delete_question(qid)
        except Exception:
            logger.exception("publish_hook: failed to delete from Qdrant qid=%s", qid)
    if question_ids:
        await db.execute(
            delete(QuestionEmbeddingMeta).where(
                QuestionEmbeddingMeta.question_id.in_(question_ids)
            )
        )
