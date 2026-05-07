import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.question import (
    Question,
    QuestionChoice,
    QuestionSet,
    QuestionSetStatus,
)
from app.models.quiz import QuizAttempt, QuizSession, QuizSessionQuestion, QuizSessionStatus
from app.models.user import User
from app.utils.pagination import Page


async def start_quiz(
    *,
    db: AsyncSession,
    user: User,
    subject_id: uuid.UUID,
    count: int,
    difficulties: list[str] | None = None,
) -> tuple[QuizSession, list[Question], dict[uuid.UUID, list[QuestionChoice]]]:
    # Pick `count` random active questions from published sets in this subject.
    query = (
        select(Question)
        .join(QuestionSet, Question.question_set_id == QuestionSet.id)
        .where(
            QuestionSet.subject_id == subject_id,
            QuestionSet.status == QuestionSetStatus.published,
            Question.is_active.is_(True),
        )
    )
    if difficulties:
        query = query.where(Question.difficulty.in_(difficulties))
    questions = list(
        await db.scalars(query.order_by(func.random()).limit(count))
    )
    if not questions:
        raise ValidationError("No published questions available for this subject")

    session = QuizSession(
        user_id=user.id,
        subject_id=subject_id,
        status=QuizSessionStatus.in_progress,
        total_questions=len(questions),
        score=0,
    )
    db.add(session)
    await db.flush()

    # Persist the picks so the session is resumable.
    for pos, q in enumerate(questions):
        db.add(QuizSessionQuestion(session_id=session.id, question_id=q.id, position=pos))
    await db.flush()

    # Load all choices in one query
    q_ids = [q.id for q in questions]
    all_choices = list(
        await db.scalars(
            select(QuestionChoice)
            .where(QuestionChoice.question_id.in_(q_ids))
            .order_by(QuestionChoice.position)
        )
    )
    choices_by_q: dict[uuid.UUID, list[QuestionChoice]] = {}
    for c in all_choices:
        choices_by_q.setdefault(c.question_id, []).append(c)

    return session, questions, choices_by_q


async def get_session(
    *, db: AsyncSession, session_id: uuid.UUID, user: User
) -> QuizSession:
    session = await db.get(QuizSession, session_id)
    if session is None:
        raise NotFoundError("QuizSession")
    if session.user_id != user.id:
        raise ForbiddenError("Not your quiz session")
    return session


async def submit_answer(
    *,
    db: AsyncSession,
    session_id: uuid.UUID,
    user: User,
    question_id: uuid.UUID,
    choice_id: uuid.UUID,
) -> tuple[QuizAttempt, uuid.UUID, str | None, int, int]:
    """Returns (attempt, correct_choice_id, explanation, answered_count, score)."""
    session = await get_session(db=db, session_id=session_id, user=user)
    if session.status != QuizSessionStatus.in_progress:
        raise ConflictError(f"Quiz is {session.status.value}")

    # Already answered this question?
    existing = await db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.session_id == session.id,
            QuizAttempt.question_id == question_id,
        )
    )
    if existing is not None:
        raise ConflictError("Question already answered")

    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError("Question")

    # Find correct choice + the chosen one
    choices = list(
        await db.scalars(
            select(QuestionChoice).where(QuestionChoice.question_id == question_id)
        )
    )
    correct = next((c for c in choices if c.is_correct), None)
    chosen = next((c for c in choices if c.id == choice_id), None)
    if correct is None:
        raise ValidationError("Question has no correct choice configured")
    if chosen is None:
        raise ValidationError("Choice does not belong to this question")

    is_correct = chosen.id == correct.id
    attempt = QuizAttempt(
        session_id=session.id,
        question_id=question.id,
        selected_choice_id=chosen.id,
        is_correct=is_correct,
    )
    db.add(attempt)
    if is_correct:
        session.score += 1
    await db.flush()

    answered_count = await db.scalar(
        select(func.count(QuizAttempt.id)).where(QuizAttempt.session_id == session.id)
    ) or 0

    return attempt, correct.id, question.explanation, answered_count, session.score


async def complete_quiz(
    *, db: AsyncSession, session_id: uuid.UUID, user: User
) -> QuizSession:
    session = await get_session(db=db, session_id=session_id, user=user)
    if session.status == QuizSessionStatus.completed:
        return session
    session.status = QuizSessionStatus.completed
    session.completed_at = datetime.now(UTC)
    await db.flush()
    return session


async def get_session_with_questions(
    *, db: AsyncSession, session_id: uuid.UUID, user: User
) -> tuple[
    QuizSession,
    list[Question],
    dict[uuid.UUID, list[QuestionChoice]],
    set[uuid.UUID],
]:
    """Returns (session, questions in original order, choices_by_q, answered_question_ids)."""
    session = await get_session(db=db, session_id=session_id, user=user)

    picks = list(
        await db.scalars(
            select(QuizSessionQuestion)
            .where(QuizSessionQuestion.session_id == session.id)
            .order_by(QuizSessionQuestion.position)
        )
    )
    if not picks:
        return session, [], {}, set()

    q_ids = [p.question_id for p in picks]
    questions_by_id = {
        q.id: q
        for q in await db.scalars(select(Question).where(Question.id.in_(q_ids)))
    }
    questions = [questions_by_id[q_id] for q_id in q_ids if q_id in questions_by_id]

    all_choices = list(
        await db.scalars(
            select(QuestionChoice)
            .where(QuestionChoice.question_id.in_(q_ids))
            .order_by(QuestionChoice.position)
        )
    )
    choices_by_q: dict[uuid.UUID, list[QuestionChoice]] = {}
    for c in all_choices:
        choices_by_q.setdefault(c.question_id, []).append(c)

    answered_ids = set(
        await db.scalars(
            select(QuizAttempt.question_id).where(QuizAttempt.session_id == session.id)
        )
    )

    return session, questions, choices_by_q, answered_ids


async def list_my_sessions(
    *,
    db: AsyncSession,
    user: User,
    page: int = 1,
    size: int = 20,
    status: QuizSessionStatus | None = None,
    subject_id: uuid.UUID | None = None,
) -> Page[QuizSession]:
    query = select(QuizSession).where(QuizSession.user_id == user.id)
    if status is not None:
        query = query.where(QuizSession.status == status)
    if subject_id is not None:
        query = query.where(QuizSession.subject_id == subject_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        await db.scalars(
            query.order_by(QuizSession.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return Page.from_list(items, total=total, page=page, size=size)


async def get_quiz_result(
    *, db: AsyncSession, session_id: uuid.UUID, user: User
) -> dict:
    """Build the full result payload: per-question breakdown, difficulty stats, trend."""
    session = await get_session(db=db, session_id=session_id, user=user)

    picks = list(
        await db.scalars(
            select(QuizSessionQuestion)
            .where(QuizSessionQuestion.session_id == session.id)
            .order_by(QuizSessionQuestion.position)
        )
    )
    q_ids = [p.question_id for p in picks]

    questions_by_id = {
        q.id: q
        for q in await db.scalars(select(Question).where(Question.id.in_(q_ids)))
    } if q_ids else {}

    all_choices = list(
        await db.scalars(
            select(QuestionChoice)
            .where(QuestionChoice.question_id.in_(q_ids))
            .order_by(QuestionChoice.position)
        )
    ) if q_ids else []
    choices_by_q: dict[uuid.UUID, list[QuestionChoice]] = {}
    for c in all_choices:
        choices_by_q.setdefault(c.question_id, []).append(c)

    attempts_by_q = {
        a.question_id: a
        for a in await db.scalars(
            select(QuizAttempt).where(QuizAttempt.session_id == session.id)
        )
    }

    correct_count = 0
    incorrect_count = 0
    skipped_count = 0
    by_diff: dict[str, dict[str, int]] = {}
    questions_payload: list[dict] = []

    for q_id in q_ids:
        question = questions_by_id.get(q_id)
        if question is None:
            continue
        choices = choices_by_q.get(q_id, [])
        correct_choice = next((c for c in choices if c.is_correct), None)
        if correct_choice is None:
            continue
        attempt = attempts_by_q.get(q_id)
        is_correct = bool(attempt and attempt.is_correct)
        selected = attempt.selected_choice_id if attempt else None

        if attempt is None:
            skipped_count += 1
        elif is_correct:
            correct_count += 1
        else:
            incorrect_count += 1

        diff = question.difficulty.value if hasattr(question.difficulty, "value") else question.difficulty
        bucket = by_diff.setdefault(str(diff), {"correct": 0, "total": 0})
        bucket["total"] += 1
        if is_correct:
            bucket["correct"] += 1

        questions_payload.append(
            {
                "question_id": question.id,
                "text": question.text,
                "difficulty": question.difficulty,
                "explanation": question.explanation,
                "selected_choice_id": selected,
                "correct_choice_id": correct_choice.id,
                "is_correct": is_correct,
                "choices": [
                    {"id": c.id, "text": c.text, "position": c.position}
                    for c in choices
                ],
            }
        )

    total = session.total_questions or len(q_ids) or 0
    accuracy = (correct_count / total) if total else 0.0

    # Trend: accuracy delta vs the most recent COMPLETED prior quiz in the same subject.
    prior = await db.scalar(
        select(QuizSession)
        .where(
            QuizSession.user_id == user.id,
            QuizSession.subject_id == session.subject_id,
            QuizSession.status == QuizSessionStatus.completed,
            QuizSession.id != session.id,
            QuizSession.created_at < session.created_at,
        )
        .order_by(QuizSession.created_at.desc())
        .limit(1)
    )
    trend: float | None = None
    if prior is not None and prior.total_questions:
        prior_acc = prior.score / prior.total_questions
        trend = round(accuracy - prior_acc, 4)

    return {
        "session_id": session.id,
        "subject_id": session.subject_id,
        "status": session.status,
        "score": session.score,
        "total": total,
        "accuracy": round(accuracy, 4),
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "skipped_count": skipped_count,
        "completed_at": session.completed_at,
        "breakdown_by_difficulty": [
            {"difficulty": k, "correct": v["correct"], "total": v["total"]}
            for k, v in by_diff.items()
        ],
        "trend": trend,
        "questions": questions_payload,
    }
