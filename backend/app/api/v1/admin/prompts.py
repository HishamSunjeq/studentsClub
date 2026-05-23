"""Admin prompt-registry endpoints (Phase 2).

CRUD for `ai_prompts` — admins manage versions of named prompts from the
frontend `PromptsPage`. Activating a version atomically deactivates any
prior active row for the same name.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select, update

from app.api.deps import AdminUser, DBSession
from app.ai import prompts_registry
from app.models.ai_prompt import AIPrompt
from app.schemas.admin import (
    PromptCreateRequest,
    PromptListResponse,
    PromptResponse,
)

router = APIRouter()


@router.get("", response_model=PromptListResponse, operation_id="admin_prompts_list")
async def list_prompts(db: DBSession, _: AdminUser, name: str | None = None) -> PromptListResponse:
    q = select(AIPrompt).order_by(AIPrompt.name.asc(), desc(AIPrompt.version))
    if name:
        q = q.where(AIPrompt.name == name)
    rows = (await db.execute(q)).scalars().all()
    return PromptListResponse(items=[PromptResponse.model_validate(r) for r in rows])


@router.post(
    "",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="admin_prompts_create",
)
async def create_prompt(
    db: DBSession, admin: AdminUser, payload: PromptCreateRequest
) -> PromptResponse:
    latest = (
        await db.execute(
            select(AIPrompt.version)
            .where(AIPrompt.name == payload.name)
            .order_by(desc(AIPrompt.version))
            .limit(1)
        )
    ).scalar_one_or_none()
    next_version = (latest or 0) + 1

    row = AIPrompt(
        name=payload.name,
        version=next_version,
        role=payload.role,
        content=payload.content,
        model_hint=payload.model_hint,
        is_active=False,
        created_by=admin.id,
    )
    db.add(row)
    await db.flush()

    if payload.activate:
        await _activate(db, row.name, row.id)
        await db.flush()

    prompts_registry.invalidate(payload.name)
    return PromptResponse.model_validate(row)


@router.post(
    "/{prompt_id}/activate",
    response_model=PromptResponse,
    operation_id="admin_prompts_activate",
)
async def activate_prompt(
    db: DBSession, _: AdminUser, prompt_id: uuid.UUID
) -> PromptResponse:
    row = (
        await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await _activate(db, row.name, row.id)
    await db.flush()
    prompts_registry.invalidate(row.name)
    await db.refresh(row)
    return PromptResponse.model_validate(row)


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="admin_prompts_delete",
)
async def delete_prompt(db: DBSession, _: AdminUser, prompt_id: uuid.UUID) -> None:
    row = (
        await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if row.is_active:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an active prompt — activate another version first.",
        )
    await db.delete(row)
    prompts_registry.invalidate(row.name)


async def _activate(db, name: str, prompt_id: uuid.UUID) -> None:
    await db.execute(
        update(AIPrompt)
        .where(AIPrompt.name == name, AIPrompt.is_active.is_(True))
        .values(is_active=False)
    )
    await db.execute(
        update(AIPrompt).where(AIPrompt.id == prompt_id).values(is_active=True)
    )
