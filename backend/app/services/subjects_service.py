import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.subject import Enrollment, Subject
from app.models.user import User
from app.utils.pagination import Page


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
