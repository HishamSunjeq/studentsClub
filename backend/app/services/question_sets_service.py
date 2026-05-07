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
    return qs


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
    *, db: AsyncSession, question_id: uuid.UUID, user: User
) -> Question:
    """Regenerate a single question in-place via the AI provider, reusing the
    original source_excerpt as the input chunk so the new question stays anchored
    to the same study material."""
    from app.ai.factory import get_provider

    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError("Question")
    qs = await _get_qs_or_404(db, question.question_set_id)
    if qs.created_by != user.id:
        raise ForbiddenError("Not your question")
    if qs.status != QuestionSetStatus.draft:
        raise ConflictError(f"Cannot edit a {qs.status.value} question set")

    seed = question.source_excerpt or question.text
    if not seed:
        raise ConflictError("Question has no source to regenerate from")

    provider = get_provider()
    result = await provider.extract_questions(
        [seed], source_type="study_material", target_count=1
    )
    if not result.questions:
        raise ConflictError("AI returned no candidate question")

    draft = result.questions[0]
    question.text = draft.text
    question.explanation = draft.explanation
    question.difficulty = draft.difficulty

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
