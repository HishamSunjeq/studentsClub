"""User profile, leaderboard, and search."""
from __future__ import annotations

import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.question import Question, QuestionSet, QuestionSetStatus
from app.models.quiz import QuizAttempt, QuizSession, QuizSessionStatus
from app.models.subject import Enrollment, Subject
from app.models.user import User


async def get_user_profile(
    *, db: AsyncSession, user_id: uuid.UUID
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User")

    # Quiz stats across all sessions
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

    completed_quizzes = (
        await db.scalar(
            select(func.count(QuizSession.id)).where(
                QuizSession.user_id == user.id,
                QuizSession.status == QuizSessionStatus.completed,
            )
        )
        or 0
    )

    # Contribution counts
    published_qs_count = (
        await db.scalar(
            select(func.count(QuestionSet.id)).where(
                QuestionSet.created_by == user.id,
                QuestionSet.status == QuestionSetStatus.published,
            )
        )
        or 0
    )
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

    # Enrolled subject count
    enrolled_subject_count = (
        await db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.user_id == user.id)
        )
        or 0
    )

    # Recent published question sets (with subject info)
    recent_rows = await db.execute(
        select(QuestionSet, Subject)
        .join(Subject, QuestionSet.subject_id == Subject.id)
        .where(
            QuestionSet.created_by == user.id,
            QuestionSet.status == QuestionSetStatus.published,
        )
        .order_by(QuestionSet.updated_at.desc())
        .limit(5)
    )
    recent_published = []
    for qs, subject in recent_rows:
        q_count = (
            await db.scalar(
                select(func.count(Question.id)).where(
                    Question.question_set_id == qs.id,
                    Question.is_active.is_(True),
                )
            )
            or 0
        )
        recent_published.append(
            {
                "question_set_id": qs.id,
                "title": qs.title,
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code,
                "question_count": int(q_count),
                "published_at": qs.updated_at,
            }
        )

    # Best single-quiz score (used for "Perfect Score" badge + display)
    best_score_row = await db.execute(
        select(QuizSession.score, QuizSession.total_questions)
        .where(
            QuizSession.user_id == user.id,
            QuizSession.status == QuizSessionStatus.completed,
            QuizSession.total_questions > 0,
        )
        .order_by((QuizSession.score * 1.0 / QuizSession.total_questions).desc())
        .limit(1)
    )
    best = best_score_row.first()
    has_perfect_score = bool(best and best[0] == best[1])

    # Streak (reuse the same logic as stats_service)
    from datetime import UTC, datetime, timedelta

    today = datetime.now(UTC).date()
    attempt_days_rows = list(
        await db.execute(
            select(func.date(QuizAttempt.answered_at).label("d"))
            .join(QuizSession, QuizAttempt.session_id == QuizSession.id)
            .where(QuizSession.user_id == user.id)
            .group_by("d")
            .order_by(func.date(QuizAttempt.answered_at).desc())
        )
    )
    attempt_days = [row[0] for row in attempt_days_rows if row[0] is not None]
    streak_days = 0
    if attempt_days:
        cursor = today
        if attempt_days[0] == today - timedelta(days=1):
            cursor = today - timedelta(days=1)
        elif attempt_days[0] != today:
            cursor = None
        if cursor is not None:
            day_set = set(attempt_days)
            while cursor in day_set:
                streak_days += 1
                cursor = cursor - timedelta(days=1)

    # Computed badges — simple milestone checks
    badges: list[dict] = []
    if completed_quizzes >= 1:
        badges.append(
            {"key": "first_quiz", "label": "First Quiz", "description": "Completed your first quiz"}
        )
    if completed_quizzes >= 10:
        badges.append(
            {"key": "active_learner", "label": "Active Learner", "description": "Completed 10 quizzes"}
        )
    if streak_days >= 3:
        badges.append(
            {"key": "streak_starter", "label": "Streak Starter", "description": "3-day practice streak"}
        )
    if streak_days >= 7:
        badges.append(
            {"key": "week_warrior", "label": "Week Warrior", "description": "7-day practice streak"}
        )
    if published_qs_count >= 1:
        badges.append(
            {"key": "first_contribution", "label": "First Contribution", "description": "Published your first question set"}
        )
    if published_qs_count >= 10:
        badges.append(
            {"key": "top_contributor", "label": "Top Contributor", "description": "Published 10 question sets"}
        )
    if has_perfect_score:
        badges.append(
            {"key": "perfect_score", "label": "Perfect Score", "description": "Aced a quiz with 100% accuracy"}
        )

    return {
        "id": user.id,
        "full_name": user.full_name,
        "college": user.college,
        "academic_year": user.academic_year,
        "joined_at": user.created_at,
        "completed_quizzes": int(completed_quizzes),
        "accuracy_avg": round(accuracy_avg, 4),
        "correct_count": int(correct_count),
        "total_attempts": int(total_attempts),
        "published_question_set_count": int(published_qs_count),
        "published_question_count": int(published_question_count),
        "enrolled_subject_count": int(enrolled_subject_count),
        "streak_days": int(streak_days),
        "badges": badges,
        "recent_published_sets": recent_published,
    }


async def get_subject_leaderboard(
    *, db: AsyncSession, subject_id: uuid.UUID, limit: int = 10
) -> list[dict]:
    """Top users in a subject ranked by composite of completed_quizzes + accuracy."""
    subject = await db.get(Subject, subject_id)
    if subject is None:
        raise NotFoundError("Subject")

    # Per-user aggregates over completed quiz sessions in this subject
    completed = (
        select(
            QuizSession.user_id.label("user_id"),
            func.count(QuizSession.id).label("completed_quizzes"),
            func.sum(QuizSession.score).label("total_correct"),
            func.sum(QuizSession.total_questions).label("total_questions"),
        )
        .where(
            QuizSession.subject_id == subject_id,
            QuizSession.status == QuizSessionStatus.completed,
            QuizSession.total_questions > 0,
        )
        .group_by(QuizSession.user_id)
        .subquery()
    )

    # Per-user contribution counts (published question sets in this subject)
    contribs = (
        select(
            QuestionSet.created_by.label("user_id"),
            func.count(QuestionSet.id).label("contributions"),
        )
        .where(
            QuestionSet.subject_id == subject_id,
            QuestionSet.status == QuestionSetStatus.published,
        )
        .group_by(QuestionSet.created_by)
        .subquery()
    )

    rows = await db.execute(
        select(
            User.id,
            User.full_name,
            func.coalesce(completed.c.completed_quizzes, 0).label("completed_quizzes"),
            func.coalesce(completed.c.total_correct, 0).label("total_correct"),
            func.coalesce(completed.c.total_questions, 0).label("total_questions"),
            func.coalesce(contribs.c.contributions, 0).label("contributions"),
        )
        .outerjoin(completed, completed.c.user_id == User.id)
        .outerjoin(contribs, contribs.c.user_id == User.id)
        .where(
            or_(
                completed.c.completed_quizzes > 0,
                contribs.c.contributions > 0,
            )
        )
        .order_by(
            (
                func.coalesce(completed.c.total_correct, 0) * 10
                + func.coalesce(contribs.c.contributions, 0) * 50
            ).desc()
        )
        .limit(limit)
    )

    out: list[dict] = []
    for row in rows:
        accuracy = (
            (row.total_correct / row.total_questions) if row.total_questions else 0.0
        )
        score = int(row.total_correct or 0) * 10 + int(row.contributions or 0) * 50
        out.append(
            {
                "user_id": row.id,
                "full_name": row.full_name,
                "completed_quizzes": int(row.completed_quizzes or 0),
                "accuracy_avg": round(accuracy, 4),
                "contributions": int(row.contributions or 0),
                "score": score,
            }
        )
    return out


async def search(
    *, db: AsyncSession, q: str, limit: int = 10
) -> dict:
    """Simple ILIKE across subjects (name/code) and published question sets (title)."""
    q_clean = q.strip()
    if not q_clean:
        return {"query": "", "subjects": [], "question_sets": []}

    pattern = f"%{q_clean}%"

    subject_rows = list(
        await db.scalars(
            select(Subject)
            .where(
                or_(
                    Subject.name.ilike(pattern),
                    Subject.code.ilike(pattern),
                    Subject.college.ilike(pattern),
                )
            )
            .limit(limit)
        )
    )

    qs_rows = await db.execute(
        select(QuestionSet, Subject)
        .join(Subject, QuestionSet.subject_id == Subject.id)
        .where(
            and_(
                QuestionSet.status == QuestionSetStatus.published,
                QuestionSet.title.ilike(pattern),
            )
        )
        .order_by(QuestionSet.updated_at.desc())
        .limit(limit)
    )

    return {
        "query": q_clean,
        "subjects": [
            {
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "college": s.college,
                "academic_year": s.academic_year,
            }
            for s in subject_rows
        ],
        "question_sets": [
            {
                "question_set_id": qs.id,
                "title": qs.title,
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code,
            }
            for qs, subject in qs_rows
        ],
    }
