import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.upload import ALLOWED_CONTENT_TYPES, Upload, UploadStatus
from app.models.user import User
from app.schemas.uploads import PresignResponse, UploadCreateRequest
from app.services import storage_service


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

    presigned_url = storage_service.generate_presigned_put_url(s3_key, payload.content_type)

    return PresignResponse(
        upload_id=upload_id,
        presigned_url=presigned_url,
        s3_key=s3_key,
    )


async def finalize_upload(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> Upload:
    upload = await _get_upload_or_404(db, upload_id)
    if upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your upload")
    if upload.status != UploadStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload is already {upload.status}",
        )
    upload.status = UploadStatus.finalized
    upload.finalized_at = datetime.now(UTC)
    await db.flush()

    from app.workers.tasks.process_upload import run as process_upload_task
    process_upload_task.delay(str(upload.id))

    return upload


async def get_upload(
    *, db: AsyncSession, upload_id: uuid.UUID, user: User
) -> Upload:
    upload = await _get_upload_or_404(db, upload_id)
    if upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your upload")
    return upload


async def _get_upload_or_404(db: AsyncSession, upload_id: uuid.UUID) -> Upload:
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload
