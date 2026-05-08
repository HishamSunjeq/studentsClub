from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.settings import (
    DensityPreference,
    NotificationType,
    ThemePreference,
)


class UserSettingsResponse(BaseModel):
    theme: ThemePreference
    accent_color: str
    density: DensityPreference
    language: str
    notification_prefs: dict[str, bool]

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    theme: ThemePreference | None = None
    accent_color: str | None = Field(default=None, max_length=32)
    density: DensityPreference | None = None
    language: str | None = Field(default=None, max_length=8)
    notification_prefs: dict[str, bool] | None = None


class NotificationResponse(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    body: str | None
    payload: dict
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    size: int
    pages: int
