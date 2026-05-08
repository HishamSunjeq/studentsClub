"""User settings + in-app notifications."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.settings import (
    DensityPreference,
    Notification,
    NotificationType,
    ThemePreference,
    UserSettings,
)
from app.models.subject import Enrollment
from app.models.user import User


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

async def get_or_create_settings(*, db: AsyncSession, user: User) -> UserSettings:
    settings = await db.scalar(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.flush()
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_settings(
    *,
    db: AsyncSession,
    user: User,
    theme: ThemePreference | None = None,
    accent_color: str | None = None,
    density: DensityPreference | None = None,
    language: str | None = None,
    notification_prefs: dict | None = None,
) -> UserSettings:
    settings = await get_or_create_settings(db=db, user=user)
    if theme is not None:
        settings.theme = theme
    if accent_color is not None:
        settings.accent_color = accent_color
    if density is not None:
        settings.density = density
    if language is not None:
        settings.language = language
    if notification_prefs is not None:
        settings.notification_prefs = notification_prefs
    await db.flush()
    await db.commit()
    await db.refresh(settings)
    return settings


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

async def list_notifications(
    *,
    db: AsyncSession,
    user: User,
    page: int = 1,
    size: int = 20,
    unread_only: bool = False,
) -> dict:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    total = (
        await db.scalar(select(func.count()).select_from(query.subquery()))
    ) or 0

    items = list(
        await db.scalars(
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )

    unread_count = (
        await db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id,
                Notification.read_at.is_(None),
            )
        )
    ) or 0

    pages = (total + size - 1) // size if total else 1
    return {
        "items": items,
        "total": int(total),
        "unread_count": int(unread_count),
        "page": page,
        "size": size,
        "pages": pages,
    }


async def mark_notification_read(
    *, db: AsyncSession, user: User, notification_id: uuid.UUID
) -> Notification:
    notif = await db.get(Notification, notification_id)
    if notif is None:
        raise NotFoundError("Notification")
    if notif.user_id != user.id:
        raise ForbiddenError("Not your notification")
    if notif.read_at is None:
        notif.read_at = datetime.now(UTC)
        await db.flush()
    return notif


async def mark_all_read(*, db: AsyncSession, user: User) -> int:
    """Bulk-mark every unread notification for this user as read. Returns count."""
    items = list(
        await db.scalars(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.read_at.is_(None),
            )
        )
    )
    now = datetime.now(UTC)
    for n in items:
        n.read_at = now
    await db.flush()
    return len(items)


# ---------------------------------------------------------------------------
# Emit helpers — called from other services on relevant events.
# Respect per-user notification_prefs (default: all-on when missing).
# ---------------------------------------------------------------------------

async def _is_enabled(
    db: AsyncSession, user_id: uuid.UUID, notif_type: NotificationType
) -> bool:
    settings = await db.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    if settings is None:
        return True  # default-on for users who never visited Settings
    prefs = settings.notification_prefs or {}
    return prefs.get(notif_type.value, True)


async def emit_notification(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
) -> Notification | None:
    if not await _is_enabled(db, user_id, type):
        return None
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        payload=payload or {},
    )
    db.add(notif)
    await db.flush()
    return notif


async def emit_question_set_published(
    *,
    db: AsyncSession,
    question_set_id: uuid.UUID,
    subject_id: uuid.UUID,
    subject_name: str,
    title: str,
    author_id: uuid.UUID,
    author_name: str,
) -> int:
    """Notify everyone enrolled in `subject_id` (except the author) that a new
    question set was published. Returns count of notifications created."""
    enrolled_ids = list(
        await db.scalars(
            select(Enrollment.user_id).where(Enrollment.subject_id == subject_id)
        )
    )
    count = 0
    for uid in enrolled_ids:
        if uid == author_id:
            continue
        notif = await emit_notification(
            db=db,
            user_id=uid,
            type=NotificationType.new_material_in_subject,
            title=f"New question set in {subject_name}",
            body=f"{author_name} published \"{title}\"",
            payload={
                "subject_id": str(subject_id),
                "question_set_id": str(question_set_id),
            },
        )
        if notif is not None:
            count += 1
    return count
