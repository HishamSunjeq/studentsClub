"""Admin extraction-settings endpoints (Phase 9).

A single global config row controls how uploaded documents are turned into
text: the backend (unstructured-api vs legacy), partition strategy, OCR
languages, and table extraction. Editing here takes effect on the next
upload (the loader cache TTL is 30s, but we invalidate eagerly).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.ai.extraction import config as extraction_config
from app.api.deps import AdminUser, DBSession
from app.models.extraction_settings import ExtractionSettings
from app.schemas.admin import (
    ExtractionSettingsResponse,
    ExtractionSettingsUpdateRequest,
)

router = APIRouter()


async def _get_row(db: DBSession) -> ExtractionSettings:
    row = (await db.execute(select(ExtractionSettings).limit(1))).scalar_one_or_none()
    if row is None:
        # Self-heal: create the singleton if the seed is missing.
        row = ExtractionSettings()
        db.add(row)
        await db.flush()
    return row


@router.get("", response_model=ExtractionSettingsResponse, operation_id="admin_extraction_get")
async def get_extraction_settings(db: DBSession, _: AdminUser) -> ExtractionSettingsResponse:
    row = await _get_row(db)
    return ExtractionSettingsResponse.model_validate(row)


@router.put("", response_model=ExtractionSettingsResponse, operation_id="admin_extraction_update")
async def update_extraction_settings(
    db: DBSession, user: AdminUser, payload: ExtractionSettingsUpdateRequest
) -> ExtractionSettingsResponse:
    row = await _get_row(db)

    fields = payload.model_dump(exclude_unset=True)
    if "ocr_languages" in fields:
        langs = [l.strip() for l in (fields["ocr_languages"] or []) if l.strip()]
        if not langs:
            raise HTTPException(status_code=422, detail="ocr_languages must not be empty")
        fields["ocr_languages"] = langs

    for key, value in fields.items():
        setattr(row, key, value)
    row.updated_by = user.id
    await db.flush()

    extraction_config.invalidate()
    return ExtractionSettingsResponse.model_validate(row)
