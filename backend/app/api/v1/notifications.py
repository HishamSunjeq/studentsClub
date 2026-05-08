from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.settings import (
    NotificationListResponse,
    NotificationResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services import notifications_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Settings (mounted under /users/me/settings — see router.py wire)
# ---------------------------------------------------------------------------

settings_router = APIRouter()


@settings_router.get(
    "",
    response_model=UserSettingsResponse,
    operation_id="settings_get",
)
async def get_my_settings(
    current_user: CurrentUser, db: DBSession
) -> UserSettingsResponse:
    settings = await notifications_service.get_or_create_settings(
        db=db, user=current_user
    )
    return UserSettingsResponse.model_validate(settings)


@settings_router.patch(
    "",
    response_model=UserSettingsResponse,
    operation_id="settings_update",
)
async def update_my_settings(
    payload: UserSettingsUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserSettingsResponse:
    settings = await notifications_service.update_settings(
        db=db,
        user=current_user,
        theme=payload.theme,
        accent_color=payload.accent_color,
        density=payload.density,
        language=payload.language,
        notification_prefs=payload.notification_prefs,
    )
    return UserSettingsResponse.model_validate(settings)


# ---------------------------------------------------------------------------
# Notifications inbox
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=NotificationListResponse,
    operation_id="notifications_list",
)
async def list_notifications(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    payload = await notifications_service.list_notifications(
        db=db, user=current_user, page=page, size=size, unread_only=unread_only
    )
    return NotificationListResponse(**payload)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    operation_id="notifications_mark_read",
)
async def mark_read(
    notification_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> NotificationResponse:
    notif = await notifications_service.mark_notification_read(
        db=db, user=current_user, notification_id=notification_id
    )
    return NotificationResponse.model_validate(notif)


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    operation_id="notifications_mark_all_read",
)
async def mark_all_read(
    current_user: CurrentUser, db: DBSession
) -> dict:
    count = await notifications_service.mark_all_read(db=db, user=current_user)
    return {"marked_read": count}
