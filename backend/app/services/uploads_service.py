import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.question import Question, QuestionSet, QuestionSetStatus
from app.models.upload import ALLOWED_CONTENT_TYPES, Upload, UploadStatus
from app.models.user import User
from app.schemas.uploads import (
    GenerateRequest,
    GenerateResponse,
    PresignResponse,
    PreviewUrlResponse,
    UploadCreateRequest,
    UploadDetailResponse,
    UploadListResponse,
    UploadQuestionSetSummary,
    UploadResponse,
    UploadUpdateRequest,
)
from app.services import storage_service

EXTRACTED_TEXT_PREVIEW_CHARS = 1500


# ---------- Create / finalize ----------


async def create_upload(
    *, db: AsyncSession, user: User, payload: UploadCreateRequest
) -> PresignResponse:
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"content_type not allowed: {payload.content_type}",
        )
    if payload.size_bytes > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File exceeds maximum size of {settings.max_upload_bytes} bytes",
        )

    upload_id = uuid.uuid4()
    s3_key = f"uploads/{user.id}/{upload_id}/{payload.filename}"

    upload = Upload(
        id=upload_id,
        user_id=user.id,
        subject_id=payload.subject_id,
        original_filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        s3_key=s3_key,
        status=UploadStatus.pending,
    )
    db.add(upload)
    await db.flush()

    presigned_url = storage_service.generate_presigned_put_url(
        s3_key, payload.content_type
    )

    return PresignResponse(
        upload_id=upload_id, presigned_url=presigned_url, s3_key=s3_key
    )


async def finalize_upload(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> Upload:
    upload = await _get_upload_or_404(db, upload_id)
    _ensure_owner(upload, user)
    if upload.status != UploadStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload is already {upload.status.value}",
        )
    upload.status = UploadStatus.extracting
    upload.finalized_at = datetime.now(UTC)
    await db.flush()

    # Fire-and-forget: text extraction only. AI generation is now user-triggered
    # via /uploads/{id}/generate.
    from app.workers.tasks.process_upload import run as extract_text_task

    extract_text_task.delay(str(upload.id))

    return upload


# ---------- Read ----------


async def list_uploads(
    *,
    db: AsyncSession,
    user: User,
    status_filter: UploadStatus | None,
    subject_id: uuid.UUID | None,
    page: int,
    size: int,
) -> UploadListResponse:
    query = select(Upload).where(Upload.user_id == user.id)
    if status_filter is not None:
        query = query.where(Upload.status == status_filter)
    if subject_id is not None:
        query = query.where(Upload.subject_id == subject_id)

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (
        await db.execute(
            query.order_by(Upload.created_at.desc())
            .limit(size)
            .offset((page - 1) * size)
        )
    ).scalars().all()

    return UploadListResponse(
        items=[UploadResponse.model_validate(u) for u in rows],
        total=total,
        page=page,
        size=size,
    )


async def get_upload(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> Upload:
    upload = await _get_upload_or_404(db, upload_id)
    _ensure_owner(upload, user)
    return upload


async def get_upload_detail(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> UploadDetailResponse:
    upload = await get_upload(db=db, upload_id=upload_id, user=user)

    qs_rows = (
        await db.execute(
            select(QuestionSet)
            .where(QuestionSet.upload_id == upload.id)
            .order_by(QuestionSet.created_at.desc())
        )
    ).scalars().all()

    qs_ids = [qs.id for qs in qs_rows]
    counts: dict[uuid.UUID, int] = {}
    if qs_ids:
        count_rows = (
            await db.execute(
                select(Question.question_set_id, func.count(Question.id))
                .where(Question.question_set_id.in_(qs_ids))
                .where(Question.is_active.is_(True))
                .group_by(Question.question_set_id)
            )
        ).all()
        counts = {row[0]: row[1] for row in count_rows}

    summaries = [
        UploadQuestionSetSummary(
            id=qs.id,
            title=qs.title,
            status=qs.status,
            created_at=qs.created_at,
            question_count=counts.get(qs.id, 0),
            generation_settings=qs.generation_settings or {},
            generation_error=qs.generation_error,
        )
        for qs in qs_rows
    ]

    preview = None
    if upload.extracted_text:
        preview = upload.extracted_text[:EXTRACTED_TEXT_PREVIEW_CHARS]

    return UploadDetailResponse(
        **UploadResponse.model_validate(upload).model_dump(),
        extracted_text_preview=preview,
        question_sets=summaries,
    )


async def get_preview_url(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> PreviewUrlResponse:
    upload = await get_upload(db=db, upload_id=upload_id, user=user)
    expires_in = 600
    url = storage_service.generate_presigned_get_url(upload.s3_key, expires_in=expires_in)
    return PreviewUrlResponse(url=url, expires_in=expires_in)


# ---------- Mutate ----------


async def update_upload(
    *,
    db: AsyncSession,
    upload_id: uuid.UUID,
    user: User,
    payload: UploadUpdateRequest,
) -> Upload:
    upload = await get_upload(db=db, upload_id=upload_id, user=user)
    if "subject_id" in payload.model_fields_set:
        upload.subject_id = payload.subject_id
    await db.flush()
    return upload


async def delete_upload(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> None:
    upload = await get_upload(db=db, upload_id=upload_id, user=user)
    s3_key = upload.s3_key
    await db.delete(upload)
    await db.flush()
    # Best-effort: remove the S3 object too. Orphan files are tolerable.
    try:
        storage_service.delete_object(s3_key)
    except Exception:
        pass


# ---------- Generate ----------


async def generate_questions(
    *,
    db: AsyncSession,
    upload_id: uuid.UUID,
    user: User,
    payload: GenerateRequest,
) -> GenerateResponse:
    upload = await get_upload(db=db, upload_id=upload_id, user=user)
    if upload.status != UploadStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Upload is {upload.status.value}; generation requires status 'ready'. "
                "Wait for extraction to finish."
            ),
        )
    if not upload.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload has no extracted text; cannot generate.",
        )

    # Phase 1 — enforce daily token budget per user before queueing.
    from app.ai.budget import check_user_daily_budget

    budget = await check_user_daily_budget(db, user.id)
    if not budget.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=budget.reason
            or "Daily token budget exhausted; please try again later.",
        )

    # Admin-only per-run overrides: validate before queueing.
    if payload.extraction_model_id is not None or payload.profile_id is not None:
        await _validate_overrides(db=db, user=user, payload=payload)

    settings_dict: dict[str, Any] = payload.model_dump(mode="json")

    qs = QuestionSet(
        upload_id=upload.id,
        subject_id=upload.subject_id,
        created_by=user.id,
        title=f"AI Draft — {upload.original_filename}",
        status=QuestionSetStatus.generating,
        ai_model="",
        tokens_used=0,
        generation_settings=settings_dict,
    )
    db.add(qs)
    await db.flush()

    # Phase 4: route through the multi-stage orchestrator. The legacy
    # `extract_questions.run` task remains as a thin compatibility shim
    # that also calls into this same workflow.
    from app.workers.tasks.ai_pipeline import run as generate_task

    generate_task.delay(str(qs.id), settings_dict)

    return GenerateResponse(question_set_id=qs.id, status=qs.status)


async def get_generation_defaults(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
):
    """Resolve which extraction model/profile would run for this upload.

    Everyone gets the resolved line; admins also get the selectable
    active extraction models + profiles for a per-run override.
    """
    from app.ai.orchestrator.profile import load_profile
    from app.models.ai_model import AIModel, ModelKind
    from app.models.generation_profile import GenerationProfile
    from app.models.user import UserRole
    from app.schemas.uploads import (
        GenerationDefaultsResponse,
        GenerationModelOption,
        GenerationProfileOption,
    )

    upload = await get_upload(db=db, upload_id=upload_id, user=user)
    profile = await load_profile(db, subject_id=upload.subject_id, profile_id=None)

    # Display name for the resolved extraction model, if it's in the registry.
    res = await db.execute(
        select(AIModel).where(
            AIModel.provider == profile.extraction_provider,
            AIModel.model_id == profile.extraction_model,
        )
    )
    model_row = res.scalar_one_or_none()
    display = model_row.display_name if model_row else profile.extraction_model

    is_admin = user.role == UserRole.admin
    models: list[GenerationModelOption] = []
    profiles: list[GenerationProfileOption] = []
    if is_admin:
        res = await db.execute(
            select(AIModel)
            .where(
                AIModel.kind == ModelKind.extraction,
                AIModel.is_active.is_(True),
            )
            .order_by(AIModel.sort_order.asc(), AIModel.model_id.asc())
        )
        models = [
            GenerationModelOption(
                id=m.id,
                display_name=m.display_name,
                model_id=m.model_id,
                provider=m.provider,
            )
            for m in res.scalars().all()
        ]
        res = await db.execute(
            select(GenerationProfile).order_by(GenerationProfile.name.asc())
        )
        profiles = [
            GenerationProfileOption(
                id=p.id,
                name=p.name,
                subject_id=p.subject_id,
                is_default=p.is_default,
            )
            for p in res.scalars().all()
        ]

    return GenerationDefaultsResponse(
        profile_id=profile.profile_id,
        profile_name=profile.name,
        extraction_provider=profile.extraction_provider,
        extraction_model=profile.extraction_model,
        extraction_model_display=display,
        is_admin=is_admin,
        models=models,
        profiles=profiles,
    )


async def _validate_overrides(
    *, db: AsyncSession, user: User, payload: GenerateRequest
) -> None:
    """Per-run model/profile overrides are admin-only and must point at
    real, active rows. Raises 403/422 otherwise.
    """
    from app.models.ai_model import AIModel, ModelKind
    from app.models.generation_profile import GenerationProfile
    from app.models.user import UserRole

    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can override the model or profile per run.",
        )

    if payload.extraction_model_id is not None:
        res = await db.execute(
            select(AIModel).where(AIModel.id == payload.extraction_model_id)
        )
        model = res.scalar_one_or_none()
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="extraction_model_id does not exist.",
            )
        if model.kind != ModelKind.extraction:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected model is not an extraction model.",
            )
        if not model.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected model is inactive.",
            )

    if payload.profile_id is not None:
        res = await db.execute(
            select(GenerationProfile).where(
                GenerationProfile.id == payload.profile_id
            )
        )
        if res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="profile_id does not exist.",
            )


# ---------- Helpers ----------


async def _get_upload_or_404(db: AsyncSession, upload_id: uuid.UUID) -> Upload:
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )
    return upload


def _ensure_owner(upload: Upload, user: User) -> None:
    if upload.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your upload"
        )
