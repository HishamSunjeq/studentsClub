"""Admin model-registry endpoints (Phase 2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, DBSession
from app.ai import registry as model_registry
from app.models.ai_model import AIModel, ModelKind
from app.schemas.admin import (
    ModelCreateRequest,
    ModelListResponse,
    ModelResponse,
    ModelUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=ModelListResponse)
async def list_models(
    db: DBSession, _: AdminUser, kind: str | None = None, provider: str | None = None
) -> ModelListResponse:
    q = select(AIModel).order_by(AIModel.sort_order.asc(), AIModel.provider.asc(), AIModel.model_id.asc())
    if kind:
        q = q.where(AIModel.kind == ModelKind(kind))
    if provider:
        q = q.where(AIModel.provider == provider)
    rows = (await db.execute(q)).scalars().all()
    return ModelListResponse(items=[ModelResponse.model_validate(r) for r in rows])


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    db: DBSession, _: AdminUser, payload: ModelCreateRequest
) -> ModelResponse:
    existing = (
        await db.execute(
            select(AIModel).where(
                AIModel.provider == payload.provider, AIModel.model_id == payload.model_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Model {payload.provider}/{payload.model_id} already exists",
        )

    row = AIModel(
        provider=payload.provider,
        model_id=payload.model_id,
        display_name=payload.display_name,
        kind=ModelKind(payload.kind),
        context_window=payload.context_window,
        max_output_tokens=payload.max_output_tokens,
        input_cost_per_mtoken=payload.input_cost_per_mtoken,
        output_cost_per_mtoken=payload.output_cost_per_mtoken,
        supports_streaming=payload.supports_streaming,
        supports_json_mode=payload.supports_json_mode,
        supports_prompt_cache=payload.supports_prompt_cache,
        embedding_dim=payload.embedding_dim,
        sort_order=payload.sort_order,
    )
    db.add(row)
    await db.flush()
    model_registry.invalidate()
    return ModelResponse.model_validate(row)


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    db: DBSession,
    _: AdminUser,
    model_id: uuid.UUID,
    payload: ModelUpdateRequest,
) -> ModelResponse:
    row = (
        await db.execute(select(AIModel).where(AIModel.id == model_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found")

    for field in (
        "display_name",
        "input_cost_per_mtoken",
        "output_cost_per_mtoken",
        "context_window",
        "max_output_tokens",
        "is_active",
        "sort_order",
    ):
        v = getattr(payload, field)
        if v is not None:
            setattr(row, field, v)
    await db.flush()
    model_registry.invalidate()
    return ModelResponse.model_validate(row)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(db: DBSession, _: AdminUser, model_id: uuid.UUID) -> None:
    row = (
        await db.execute(select(AIModel).where(AIModel.id == model_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found")
    await db.delete(row)
    model_registry.invalidate()
