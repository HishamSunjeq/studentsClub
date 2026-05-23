"""Text-extraction worker. Runs after a successful upload finalize.

This worker is intentionally narrow: it pulls the file from S3, extracts text,
and persists it on the Upload row. AI generation is now a separate, user-triggered
step (see `extract_questions.run` invoked from `uploads_service.generate_questions`).
"""

import asyncio
import uuid
from datetime import UTC, datetime

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_upload.run", bind=True, max_retries=3)
def run(self, upload_id: str) -> dict:  # type: ignore[return]
    try:
        return asyncio.run(_async_run(upload_id))
    except Exception as exc:
        # Last-retry: persist the failure state so the UI can show it.
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(upload_id, str(exc)))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _async_run(upload_id: str) -> dict:
    from sqlalchemy import select

    from app.ai.parsers import extract_text
    from app.core.database import AsyncSessionLocal
    from app.models.upload import Upload, UploadStatus
    from app.services import storage_service

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Upload).where(Upload.id == uuid.UUID(upload_id))
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise ValueError(f"Upload {upload_id} not found")

        s3_key = upload.s3_key
        content_type = upload.content_type

    content = storage_service.download_file(s3_key)
    text = extract_text(content, content_type)

    if not text.strip():
        raise ValueError(f"No text extracted from upload {upload_id}")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                select(Upload).where(Upload.id == uuid.UUID(upload_id))
            )
            upload = result.scalar_one()
            upload.extracted_text = text
            upload.extracted_at = datetime.now(UTC)
            upload.extraction_error = None
            upload.status = UploadStatus.ready

    # Phase 3: chain into the RAG embedding pipeline. Best-effort dispatch —
    # if Redis/Celery is misconfigured we still return success on extraction.
    try:
        from app.workers.tasks.embed_chunks import run as embed_run

        embed_run.apply_async(args=[upload_id], queue="embeddings")
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to dispatch embed_chunks for upload=%s", upload_id
        )

    return {"upload_id": upload_id, "chars": len(text)}


async def _mark_failed(upload_id: str, message: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.upload import Upload, UploadStatus

    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                select(Upload).where(Upload.id == uuid.UUID(upload_id))
            )
            upload = result.scalar_one_or_none()
            if upload is None:
                return
            upload.status = UploadStatus.failed
            upload.extraction_error = message[:2000]
