"""Admin telemetry browser over `ai_runs` (Phase 6).

Read-only, paginated, filterable. The rollup totals are computed over the
whole filtered set (not just the current page) so the UI can show
spend/usage for any slice.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import AdminUser, DBSession
from app.models.ai_run import AIRun, AIRunStatus
from app.schemas.admin import (
    AIRunDetailResponse,
    AIRunListResponse,
    AIRunResponse,
)

router = APIRouter()


def _apply_filters(
    q,
    *,
    question_set_id: uuid.UUID | None,
    provider: str | None,
    model: str | None,
    credential_alias: str | None,
    status: str | None,
    since: datetime | None,
    until: datetime | None,
):
    if question_set_id is not None:
        q = q.where(AIRun.question_set_id == question_set_id)
    if provider:
        q = q.where(AIRun.provider == provider)
    if model:
        q = q.where(AIRun.model == model)
    if credential_alias:
        q = q.where(AIRun.credential_alias == credential_alias)
    if status:
        q = q.where(AIRun.status == AIRunStatus(status))
    if since is not None:
        q = q.where(AIRun.created_at >= since)
    if until is not None:
        q = q.where(AIRun.created_at <= until)
    return q


@router.get("", response_model=AIRunListResponse)
async def list_ai_runs(
    db: DBSession,
    _: AdminUser,
    question_set_id: uuid.UUID | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    credential_alias: str | None = Query(default=None),
    status: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> AIRunListResponse:
    filters = dict(
        question_set_id=question_set_id,
        provider=provider,
        model=model,
        credential_alias=credential_alias,
        status=status,
        since=since,
        until=until,
    )

    rollup_q = _apply_filters(
        select(
            func.coalesce(func.sum(AIRun.cost_usd), 0),
            func.coalesce(func.sum(AIRun.input_tokens), 0),
            func.coalesce(func.sum(AIRun.output_tokens), 0),
            func.count(),
        ),
        **filters,
    )
    total_cost, total_in, total_out, total = (await db.execute(rollup_q)).one()

    rows_q = _apply_filters(select(AIRun), **filters).order_by(
        AIRun.created_at.desc()
    ).offset((page - 1) * size).limit(size)
    rows = (await db.execute(rows_q)).scalars().all()

    return AIRunListResponse(
        items=[AIRunResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        size=size,
        total_cost_usd=total_cost,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
    )


@router.get("/{run_id}", response_model=AIRunDetailResponse)
async def get_ai_run(
    db: DBSession, _: AdminUser, run_id: uuid.UUID
) -> AIRunDetailResponse:
    row = (
        await db.execute(select(AIRun).where(AIRun.id == run_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="AI run not found")
    return AIRunDetailResponse.model_validate(row)
