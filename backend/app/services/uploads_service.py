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

    settings_dict: dict[str, Any] = payload.model_dump()

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

    from app.workers.tasks.extract_questions import run as generate_task

    generate_task.delay(str(qs.id), settings_dict)

    return GenerateResponse(question_set_id=qs.id, status=qs.status)


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
