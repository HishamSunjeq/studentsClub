import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.question import (
    Question,
    QuestionChoice,
    QuestionSet,
    QuestionSetStatus,
)
from app.models.user import User
from app.schemas.question_sets import QuestionUpdateRequest
from app.utils.pagination import Page


async def list_my_drafts(
    *,
    db: AsyncSession,
    user: User,
    status: QuestionSetStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> Page[QuestionSet]:
    query = select(QuestionSet).where(QuestionSet.created_by == user.id)
    if status is not None:
        query = query.where(QuestionSet.status == status)

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        await db.scalars(
            query.order_by(QuestionSet.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return Page.from_list(items, total=total, page=page, size=size)


async def get_with_questions(
    *, db: AsyncSession, qs_id: uuid.UUID, user: User
) -> QuestionSet:
    qs = await db.get(QuestionSet, qs_id)
    if qs is None:
        raise NotFoundError("QuestionSet")
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question set")

    # Load questions + choices, ordered. Done as separate queries because Question
    # has no relationship attribute defined on the model — we just query directly.
    questions = list(
        await db.scalars(
            select(Question)
            .where(Question.question_set_id == qs.id)
            .order_by(Question.position)
        )
    )
    choices_by_q: dict[uuid.UUID, list[QuestionChoice]] = {}
    if questions:
        q_ids = [q.id for q in questions]
        all_choices = list(
            await db.scalars(
                select(QuestionChoice)
                .where(QuestionChoice.question_id.in_(q_ids))
                .order_by(QuestionChoice.position)
            )
        )
        for c in all_choices:
            choices_by_q.setdefault(c.question_id, []).append(c)

    # Attach as transient attribute so the response schema can read it
    for q in questions:
        q.choices = choices_by_q.get(q.id, [])  # type: ignore[attr-defined]
    qs.questions = questions  # type: ignore[attr-defined]
    return qs


async def update_title(
    *, db: AsyncSession, qs_id: uuid.UUID, user: User, title: str
) -> QuestionSet:
    qs = await _get_qs_or_404(db, qs_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question set")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Cannot edit a {qs.status.value} question set")
    qs.title = title
    await db.flush()
    await db.refresh(qs)
    return qs


async def publish(
    *, db: AsyncSession, qs_id: uuid.UUID, user: User
) -> QuestionSet:
    from app.models.subject import Subject
    from app.services import notifications_service

    qs = await _get_qs_or_404(db, qs_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question set")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Already {qs.status.value}")

    active_count = await db.scalar(
        select(func.count(Question.id)).where(
            Question.question_set_id == qs.id,
            Question.is_active.is_(True),
        )
    ) or 0
    if active_count == 0:
        raise ConflictError("Cannot publish a set with no active questions")

    qs.status = QuestionSetStatus.published
    await db.flush()
    await db.refresh(qs)

    # Phase 4: upsert accepted questions into Qdrant `questions` collection so
    # they participate in dedup for future generations within the same subject.
    try:
        from app.ai.orchestrator.publish_hook import upsert_accepted_questions

        await upsert_accepted_questions(
            db, question_set_id=qs.id, subject_id=qs.subject_id, published=True
        )
    except Exception:
        # Best-effort: a Qdrant outage must not block publish.
        import logging

        logging.getLogger(__name__).exception(
            "publish: Qdrant upsert failed for qs=%s", qs.id
        )

    # Fan out notifications to enrolled subject members (other than the author).
    if qs.subject_id is not None:
        subject = await db.get(Subject, qs.subject_id)
        if subject is not None:
            await notifications_service.emit_question_set_published(
                db=db,
                question_set_id=qs.id,
                subject_id=subject.id,
                subject_name=subject.name,
                title=qs.title,
                author_id=user.id,
                author_name=user.full_name,
            )

    return qs


async def reject(
    *, db: AsyncSession, qs_id: uuid.UUID, user: User
) -> QuestionSet:
    qs = await _get_qs_or_404(db, qs_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question set")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Already {qs.status.value}")
    qs.status = QuestionSetStatus.rejected
    await db.flush()
    await db.refresh(qs)

    # Phase 4: remove any previously-indexed questions from the Qdrant bank.
    try:
        from app.ai.orchestrator.publish_hook import remove_questions_from_bank

        q_ids = list(
            await db.scalars(
                select(Question.id).where(Question.question_set_id == qs.id)
            )
        )
        if q_ids:
            await remove_questions_from_bank(db, question_ids=q_ids)
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "reject: Qdrant cleanup failed for qs=%s", qs.id
        )
    return qs


async def replay(
    *,
    db: AsyncSession,
    qs_id: uuid.UUID,
    user: User,
    overrides: dict | None = None,
) -> QuestionSet:
    """Clone a QuestionSet and re-run generation against the same upload,
    optionally overriding the profile / prompt version / model / credential.
    The clone links back via `parent_question_set_id` for diffing and audit."""
    parent = await _get_qs_or_404(db, qs_id)
    if parent.created_by != user.id:
        raise ForbiddenError("Not your question set")

    overrides = {k: v for k, v in (overrides or {}).items() if v is not None}
    # Inherit the original generation settings, layering any overrides on top.
    settings_dict: dict = dict(parent.generation_settings or {})
    settings_dict.update({str(k): str(v) for k, v in overrides.items()})

    clone = QuestionSet(
        upload_id=parent.upload_id,
        subject_id=parent.subject_id,
        created_by=user.id,
        title=f"{parent.title} (replay)",
        status=QuestionSetStatus.generating,
        ai_model="",
        tokens_used=0,
        generation_settings=settings_dict,
        parent_question_set_id=parent.id,
    )
    db.add(clone)
    await db.flush()
    await db.refresh(clone)

    from app.workers.tasks.ai_pipeline import run as generate_task

    generate_task.delay(str(clone.id), settings_dict)
    return clone


async def update_question(
    *,
    db: AsyncSession,
    question_id: uuid.UUID,
    user: User,
    payload: QuestionUpdateRequest,
) -> Question:
    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError("Question")
    qs = await _get_qs_or_404(db, question.question_set_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Cannot edit a {qs.status.value} question set")

    if payload.text is not None:
        question.text = payload.text
    if payload.explanation is not None:
        question.explanation = payload.explanation
    if payload.difficulty is not None:
        question.difficulty = payload.difficulty

    if payload.choices is not None:
        # Replace all existing choices with the new ones.
        existing = list(
            await db.scalars(
                select(QuestionChoice).where(QuestionChoice.question_id == question.id)
            )
        )
        for c in existing:
            await db.delete(c)
        await db.flush()
        for pos, c in enumerate(payload.choices):
            db.add(
                QuestionChoice(
                    question_id=question.id,
                    text=c.text,
                    is_correct=c.is_correct,
                    position=pos,
                )
            )

    await db.flush()
    return question


async def regenerate_question(
    *,
    db: AsyncSession,
    question_id: uuid.UUID,
    user: User,
    chunk_ids: list[uuid.UUID] | None = None,
) -> Question:
    """Regenerate a single question in-place via the AI provider.

    When `chunk_ids` is provided, those chunks are concatenated as the RAG
    context window so the re-prompt is grounded in (potentially different)
    material than the original draft. Otherwise we fall back to the original
    `source_excerpt`.
    """
    from app.ai.factory import get_provider
    from app.models.document_chunk import DocumentChunk

    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError("Question")
    qs = await _get_qs_or_404(db, question.question_set_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Cannot edit a {qs.status.value} question set")

    seeds: list[str] = []
    new_chunk_ids: list[uuid.UUID] = []
    if chunk_ids:
        rows = (
            await db.execute(
                select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
            )
        ).scalars().all()
        by_id = {r.id: r for r in rows}
        for cid in chunk_ids:
            row = by_id.get(cid)
            if row and row.text:
                seeds.append(row.text)
                new_chunk_ids.append(row.id)

    if not seeds:
        fallback = question.source_excerpt or question.text
        if not fallback:
            raise ConflictError("Question has no source to regenerate from")
        seeds = [fallback]

    provider = get_provider()
    result = await provider.extract_questions(
        seeds, source_type="study_material", target_count=1
    )
    if not result.questions:
        raise ConflictError("AI returned no candidate question")

    draft = result.questions[0]
    question.text = draft.text
    question.explanation = draft.explanation
    question.difficulty = draft.difficulty
    if new_chunk_ids:
        question.source_chunk_ids = new_chunk_ids

    # Replace all choices with the new draft's choices
    existing = list(
        await db.scalars(
            select(QuestionChoice).where(QuestionChoice.question_id == question.id)
        )
    )
    for c in existing:
        await db.delete(c)
    await db.flush()
    for pos, c in enumerate(draft.choices):
        db.add(
            QuestionChoice(
                question_id=question.id,
                text=c.text,
                is_correct=c.is_correct,
                position=pos,
            )
        )
    await db.flush()
    return question


async def retrieval_preview_for_question(
    *, db: AsyncSession, question_id: uuid.UUID, user: User
):
    """Run the RAG retrieve stage with the question's current text as the query.

    Returns the top reranked chunks the user can choose to regenerate against.
    Imported lazily to avoid circular deps with the orchestrator at module load.
    """
    from app.ai.orchestrator.profile import load_profile
    from app.ai.orchestrator.schemas import Section
    from app.ai.orchestrator.stages.retrieve import retrieve_for_section

    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError("Question")
    qs = await _get_qs_or_404(db, question.question_set_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question")

    profile = await load_profile(db, subject_id=qs.subject_id)
    section = Section(
        position=question.position,
        title=question.text[:120],
        text=question.text + "\n\n" + (question.explanation or ""),
        target_questions=1,
    )
    return await retrieve_for_section(
        profile=profile,
        section=section,
        subject_id=qs.subject_id,
        upload_id=qs.upload_id,
        question_set_id=qs.id,
        user_id=user.id,
    )


async def deactivate_question(
    *, db: AsyncSession, question_id: uuid.UUID, user: User
) -> None:
    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError("Question")
    qs = await _get_qs_or_404(db, question.question_set_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Cannot edit a {qs.status.value} question set")
    question.is_active = False
    await db.flush()


async def _get_qs_or_404(db: AsyncSession, qs_id: uuid.UUID) -> QuestionSet:
    qs = await db.get(QuestionSet, qs_id)
    if qs is None:
        raise NotFoundError("QuestionSet")
    return qs
