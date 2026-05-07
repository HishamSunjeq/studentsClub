import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.question import Question, QuestionSet, QuestionSetStatus
from app.models.subject import Enrollment, Subject
from app.models.user import User
from app.schemas.subjects import (
    SubjectContributorResponse,
    SubjectMemberResponse,
    SubjectPublishedSetResponse,
)
from app.utils.pagination import Page


async def compute_aggregates(
    db: AsyncSession,
    subject_ids: list[uuid.UUID],
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    """Returns (member_counts, qs_counts, question_counts) keyed by subject_id."""
    if not subject_ids:
        return {}, {}, {}

    member_rows = await db.execute(
        select(Enrollment.subject_id, func.count(Enrollment.id).label("cnt"))
        .where(Enrollment.subject_id.in_(subject_ids))
        .group_by(Enrollment.subject_id)
    )
    member_counts: dict[uuid.UUID, int] = {row.subject_id: row.cnt for row in member_rows}

    qs_rows = await db.execute(
        select(QuestionSet.subject_id, func.count(QuestionSet.id).label("cnt"))
        .where(
            QuestionSet.subject_id.in_(subject_ids),
            QuestionSet.status == QuestionSetStatus.published,
        )
        .group_by(QuestionSet.subject_id)
    )
    qs_counts: dict[uuid.UUID, int] = {row.subject_id: row.cnt for row in qs_rows}

    q_rows = await db.execute(
        select(QuestionSet.subject_id, func.count(Question.id).label("cnt"))
        .join(Question, Question.question_set_id == QuestionSet.id)
        .where(
            QuestionSet.subject_id.in_(subject_ids),
            QuestionSet.status == QuestionSetStatus.published,
            Question.is_active.is_(True),
        )
        .group_by(QuestionSet.subject_id)
    )
    q_counts: dict[uuid.UUID, int] = {row.subject_id: row.cnt for row in q_rows}

    return member_counts, qs_counts, q_counts


async def list_subjects(
    *,
    db: AsyncSession,
    college: str | None = None,
    academic_year: int | None = None,
    page: int = 1,
    size: int = 20,
) -> Page[Subject]:
    query = select(Subject)
    if college:
        query = query.where(Subject.college == college)
    if academic_year is not None:
        query = query.where(Subject.academic_year == academic_year)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    items = list(
        await db.scalars(
            query.order_by(Subject.college, Subject.academic_year, Subject.code)
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return Page.from_list(items, total=total, page=page, size=size)


async def get_subject(*, db: AsyncSession, subject_id: uuid.UUID) -> Subject:
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject")
    return subject


async def enroll(*, db: AsyncSession, user: User, subject_id: uuid.UUID) -> Enrollment:
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject")

    existing = await db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.subject_id == subject_id,
        )
    )
    if existing:
        raise ConflictError("Already enrolled in this subject")

    enrollment = Enrollment(user_id=user.id, subject_id=subject_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def unenroll(*, db: AsyncSession, user: User, subject_id: uuid.UUID) -> None:
    enrollment = await db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.subject_id == subject_id,
        )
    )
    if not enrollment:
        raise NotFoundError("Enrollment")
    await db.delete(enrollment)
    await db.commit()


async def my_subjects(
    *,
    db: AsyncSession,
    user: User,
    page: int = 1,
    size: int = 20,
) -> Page[Subject]:
    enrolled_ids = select(Enrollment.subject_id).where(Enrollment.user_id == user.id)
    query = select(Subject).where(Subject.id.in_(enrolled_ids))

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    items = list(
        await db.scalars(
            query.order_by(Subject.college, Subject.academic_year, Subject.code)
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return Page.from_list(items, total=total, page=page, size=size)


async def get_members(
    *,
    db: AsyncSession,
    subject_id: uuid.UUID,
    page: int = 1,
    size: int = 20,
) -> tuple[list[SubjectMemberResponse], int]:
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject")

    base = (
        select(User.id, User.full_name, User.college, User.academic_year, Enrollment.enrolled_at)
        .join(Enrollment, User.id == Enrollment.user_id)
        .where(Enrollment.subject_id == subject_id)
    )
    total = await db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    rows = await db.execute(
        base.order_by(Enrollment.enrolled_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    members = [
        SubjectMemberResponse(
            user_id=row.id,
            full_name=row.full_name,
            college=row.college,
            academic_year=row.academic_year,
            enrolled_at=row.enrolled_at,
        )
        for row in rows
    ]
    return members, total


async def get_top_contributors(
    *,
    db: AsyncSession,
    subject_id: uuid.UUID,
    limit: int = 10,
) -> list[SubjectContributorResponse]:
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject")

    rows = await db.execute(
        select(
            User.id,
            User.full_name,
            func.count(QuestionSet.id).label("question_set_count"),
        )
        .join(QuestionSet, QuestionSet.created_by == User.id)
        .where(
            QuestionSet.subject_id == subject_id,
            QuestionSet.status == QuestionSetStatus.published,
        )
        .group_by(User.id, User.full_name)
        .order_by(func.count(QuestionSet.id).desc())
        .limit(limit)
    )
    return [
        SubjectContributorResponse(
            user_id=row.id,
            full_name=row.full_name,
            question_set_count=row.question_set_count,
        )
        for row in rows
    ]


async def get_published_sets(
    *,
    db: AsyncSession,
    subject_id: uuid.UUID,
    page: int = 1,
    size: int = 20,
) -> tuple[list[SubjectPublishedSetResponse], int]:
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise NotFoundError("Subject")

    q_count_subq = (
        select(func.count(Question.id))
        .where(
            Question.question_set_id == QuestionSet.id,
            Question.is_active.is_(True),
        )
        .scalar_subquery()
    )

    total = await db.scalar(
        select(func.count(QuestionSet.id)).where(
            QuestionSet.subject_id == subject_id,
            QuestionSet.status == QuestionSetStatus.published,
        )
    ) or 0

    rows = await db.execute(
        select(
            QuestionSet.id,
            QuestionSet.title,
            QuestionSet.created_at,
            q_count_subq.label("question_count"),
        )
        .where(
            QuestionSet.subject_id == subject_id,
            QuestionSet.status == QuestionSetStatus.published,
        )
        .order_by(QuestionSet.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return [
        SubjectPublishedSetResponse(
            id=row.id,
            title=row.title,
            created_at=row.created_at,
            question_count=row.question_count,
        )
        for row in rows
    ], total
