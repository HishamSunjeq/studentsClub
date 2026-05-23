"""Admin generation-profile endpoints (Phase 2).

A `GenerationProfile` references the model registry by id and the
credential store by alias. Marking a profile `is_default=true`
deactivates the prior default in the same scope (global or per-subject).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.api.deps import AdminUser, DBSession
from app.models.ai_model import AIModel
from app.models.generation_profile import GenerationProfile
from app.schemas.admin import (
    ProfileCreateRequest,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    db: DBSession, _: AdminUser, subject_id: uuid.UUID | None = None
) -> ProfileListResponse:
    q = select(GenerationProfile).order_by(
        GenerationProfile.subject_id.asc().nulls_first(),
        GenerationProfile.name.asc(),
    )
    if subject_id is not None:
        q = q.where(GenerationProfile.subject_id == subject_id)
    rows = (await db.execute(q)).scalars().all()
    return ProfileListResponse(items=[ProfileResponse.model_validate(r) for r in rows])


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    db: DBSession, _: AdminUser, payload: ProfileCreateRequest
) -> ProfileResponse:
    await _validate_model_refs(db, payload)

    row = GenerationProfile(
        subject_id=payload.subject_id,
        name=payload.name,
        prompt_name=payload.prompt_name,
        judge_prompt_name=payload.judge_prompt_name,
        extraction_model_id=payload.extraction_model_id,
        judge_model_id=payload.judge_model_id,
        embedding_model_id=payload.embedding_model_id,
        rerank_model_id=payload.rerank_model_id,
        credential_alias_extraction=payload.credential_alias_extraction,
        credential_alias_judge=payload.credential_alias_judge,
        credential_alias_embedding=payload.credential_alias_embedding,
        credential_alias_rerank=payload.credential_alias_rerank,
        target_count=payload.target_count,
        difficulty_mix=payload.difficulty_mix,
        judge_threshold=payload.judge_threshold,
        dedup_threshold=payload.dedup_threshold,
        top_k_retrieval=payload.top_k_retrieval,
        top_n_rerank=payload.top_n_rerank,
        hybrid_alpha=payload.hybrid_alpha,
        is_default=payload.is_default,
    )
    db.add(row)
    await db.flush()
    if payload.is_default:
        await _enforce_single_default(db, row)
    return ProfileResponse.model_validate(row)


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    db: DBSession,
    _: AdminUser,
    profile_id: uuid.UUID,
    payload: ProfileUpdateRequest,
) -> ProfileResponse:
    row = (
        await db.execute(
            select(GenerationProfile).where(GenerationProfile.id == profile_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    await _validate_model_refs(db, payload)

    for field in payload.model_fields_set:
        setattr(row, field, getattr(payload, field))
    await db.flush()

    if row.is_default:
        await _enforce_single_default(db, row)

    return ProfileResponse.model_validate(row)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(db: DBSession, _: AdminUser, profile_id: uuid.UUID) -> None:
    row = (
        await db.execute(
            select(GenerationProfile).where(GenerationProfile.id == profile_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(row)


async def _validate_model_refs(db, payload) -> None:
    """422 if any model_id in the payload points to an inactive/missing row."""
    for field in (
        "extraction_model_id",
        "judge_model_id",
        "embedding_model_id",
        "rerank_model_id",
    ):
        model_id = getattr(payload, field, None)
        if model_id is None:
            continue
        m = (
            await db.execute(select(AIModel).where(AIModel.id == model_id))
        ).scalar_one_or_none()
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} references unknown model",
            )
        if not m.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} references inactive model {m.provider}/{m.model_id}",
            )


async def _enforce_single_default(db, row: GenerationProfile) -> None:
    """Demote any other default in the same scope."""
    q = update(GenerationProfile).values(is_default=False).where(
        GenerationProfile.id != row.id,
        GenerationProfile.is_default.is_(True),
    )
    if row.subject_id is None:
        q = q.where(GenerationProfile.subject_id.is_(None))
    else:
        q = q.where(GenerationProfile.subject_id == row.subject_id)
    await db.execute(q)
