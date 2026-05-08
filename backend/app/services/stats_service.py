"""Aggregate stats and activity feed for the dashboard."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question, QuestionSet, QuestionSetStatus
from app.models.quiz import QuizAttempt, QuizSession, QuizSessionStatus
from app.models.subject import Enrollment, Subject
from app.models.user import User

# Default weekly target until per-user settings ship in Phase 10.
DEFAULT_WEEKLY_GOAL = 5

# XP formula constants
XP_PER_CORRECT_ANSWER = 10
XP_PER_PUBLISHED_QUESTION = 5


async def get_user_stats(*, db: AsyncSession, user: User) -> dict:
    today = datetime.now(UTC).date()

    # All distinct attempt-days (UTC) for this user, newest first.
    attempt_days_rows = list(
        await db.execute(
            select(func.date(QuizAttempt.answered_at).label("d"))
            .join(QuizSession, QuizAttempt.session_id == QuizSession.id)
            .where(QuizSession.user_id == user.id)
            .group_by("d")
            .order_by(func.date(QuizAttempt.answered_at).desc())
        )
    )
    attempt_days: list[date] = [row[0] for row in attempt_days_rows if row[0] is not None]

    # Streak: consecutive days back from today (or yesterday — gracefully handle
    # late-night users) with at least one attempt.
    streak_days = 0
    if attempt_days:
        cursor = today
        # If the most recent day is yesterday, anchor the streak there so a user
        # who already practised yesterday but not yet today still sees the chain.
        if attempt_days[0] == today - timedelta(days=1):
            cursor = today - timedelta(days=1)
        elif attempt_days[0] != today:
            cursor = None
        if cursor is not None:
            day_set = set(attempt_days)
            while cursor in day_set:
                streak_days += 1
                cursor = cursor - timedelta(days=1)

    # Accuracy + XP from quiz attempts
    correct_count = (
        await db.scalar(
            select(func.count(QuizAttempt.id))
            .join(QuizSession, QuizAttempt.session_id == QuizSession.id)
            .where(QuizSession.user_id == user.id, QuizAttempt.is_correct.is_(True))
        )
        or 0
    )
    total_attempts = (
        await db.scalar(
            select(func.count(QuizAttempt.id))
            .join(QuizSession, QuizAttempt.session_id == QuizSession.id)
            .where(QuizSession.user_id == user.id)
        )
        or 0
    )
    accuracy_avg = (correct_count / total_attempts) if total_attempts else 0.0

    # Published-question contribution toward XP — count active questions inside
    # this user's published sets.
    published_question_count = (
        await db.scalar(
            select(func.count(Question.id))
            .join(QuestionSet, Question.question_set_id == QuestionSet.id)
            .where(
                QuestionSet.created_by == user.id,
                QuestionSet.status == QuestionSetStatus.published,
                Question.is_active.is_(True),
            )
        )
        or 0
    )

    xp_total = (
        XP_PER_CORRECT_ANSWER * correct_count
        + XP_PER_PUBLISHED_QUESTION * published_question_count
    )

    # Weekly progress — completed quiz sessions in the current ISO week (Mon-Sun, UTC).
    week_start = datetime.combine(
        today - timedelta(days=today.weekday()),
        datetime.min.time(),
        tzinfo=UTC,
    )
    weekly_progress = (
        await db.scalar(
            select(func.count(QuizSession.id)).where(
                QuizSession.user_id == user.id,
                QuizSession.status == QuizSessionStatus.completed,
                QuizSession.completed_at >= week_start,
            )
        )
        or 0
    )

    # Drafts awaiting the user's own review
    drafts_pending = (
        await db.scalar(
            select(func.count(QuestionSet.id)).where(
                QuestionSet.created_by == user.id,
                QuestionSet.status == QuestionSetStatus.draft,
            )
        )
        or 0
    )

    return {
        "streak_days": int(streak_days),
        "xp_total": int(xp_total),
        "weekly_goal": DEFAULT_WEEKLY_GOAL,
        "weekly_progress": int(weekly_progress),
        "accuracy_avg": round(accuracy_avg, 4),
        "correct_count": int(correct_count),
        "total_attempts": int(total_attempts),
        "drafts_pending_review_count": int(drafts_pending),
        "published_question_count": int(published_question_count),
    }


async def get_activity_feed(
    *, db: AsyncSession, user: User, page: int = 1, size: int = 20
) -> dict:
    """Recent published question sets in subjects this user is enrolled in.
    Excludes the user's own publications so the feed feels social."""
    # Enrolled subject ids
    enrolled_ids = list(
        await db.scalars(
            select(Enrollment.subject_id).where(Enrollment.user_id == user.id)
        )
    )

    if not enrolled_ids:
        return {"items": [], "total": 0, "page": page, "size": size, "pages": 1}

    base = (
        select(QuestionSet, Subject, User)
        .join(Subject, QuestionSet.subject_id == Subject.id)
        .join(User, QuestionSet.created_by == User.id)
        .where(
            QuestionSet.subject_id.in_(enrolled_ids),
            QuestionSet.status == QuestionSetStatus.published,
            QuestionSet.created_by != user.id,
        )
    )

    total = (
        await db.scalar(select(func.count()).select_from(base.subquery()))
    ) or 0

    rows = list(
        await db.execute(
            base.order_by(QuestionSet.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )

    items = []
    for qs, subject, author in rows:
        # Count active questions in the set
        q_count = (
            await db.scalar(
                select(func.count(Question.id)).where(
                    Question.question_set_id == qs.id,
                    Question.is_active.is_(True),
                )
            )
            or 0
        )
        items.append(
            {
                "question_set_id": qs.id,
                "title": qs.title,
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code,
                "author_id": author.id,
                "author_name": author.full_name,
                "question_count": int(q_count),
                "published_at": qs.updated_at,
            }
        )

    pages = (total + size - 1) // size if total else 1
    return {
        "items": items,
        "total": int(total),
        "page": page,
        "size": size,
        "pages": pages,
    }


async def get_recommended_subjects(
    *, db: AsyncSession, user: User, limit: int = 4
) -> list[Subject]:
    """Subjects the user isn't enrolled in yet, prioritising same-college and
    same-year matches. Used by the dashboard 'Recommended' tile."""
    enrolled_ids = list(
        await db.scalars(
            select(Enrollment.subject_id).where(Enrollment.user_id == user.id)
        )
    )

    query = select(Subject)
    if enrolled_ids:
        query = query.where(Subject.id.notin_(enrolled_ids))
    query = query.where(
        (Subject.college == user.college) | (Subject.academic_year == user.academic_year)
    ).limit(limit)

    return list(await db.scalars(query))


async def get_continue_session(
    *, db: AsyncSession, user: User
) -> tuple[QuizSession, Subject] | None:
    """Most recent in-progress quiz, used by the 'Continue where you left off' tile."""
    row = (
        await db.execute(
            select(QuizSession, Subject)
            .join(Subject, QuizSession.subject_id == Subject.id)
            .where(
                QuizSession.user_id == user.id,
                QuizSession.status == QuizSessionStatus.in_progress,
            )
            .order_by(QuizSession.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return row[0], row[1]


async def get_continue_session_progress(
    *, db: AsyncSession, session_id: uuid.UUID
) -> int:
    """Number of questions answered in a session so far."""
    return (
        await db.scalar(
            select(func.count(QuizAttempt.id)).where(
                QuizAttempt.session_id == session_id
            )
        )
        or 0
    )
