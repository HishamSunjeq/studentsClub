import asyncio
import uuid

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_upload.run", bind=True, max_retries=3)
def run(self, upload_id: str) -> dict:  # type: ignore[return]
    try:
        return asyncio.run(_async_run(upload_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _async_run(upload_id: str) -> dict:
    from sqlalchemy import select

    from app.ai.parsers import chunk_text, extract_text
    from app.core.database import AsyncSessionLocal
    from app.models.upload import Upload
    from app.services import storage_service
    from app.workers.tasks.extract_questions import run as extract_task

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Upload).where(Upload.id == uuid.UUID(upload_id))
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise ValueError(f"Upload {upload_id} not found")

        s3_key = upload.s3_key
        content_type = upload.content_type
        user_id = str(upload.user_id)
        subject_id = str(upload.subject_id) if upload.subject_id else None

    content = storage_service.download_file(s3_key)
    text = extract_text(content, content_type)

    if not text.strip():
        raise ValueError(f"No text extracted from upload {upload_id}")

    chunks = chunk_text(text)
    extract_task.delay(upload_id, chunks, user_id, subject_id)

    return {"upload_id": upload_id, "chunks": len(chunks), "chars": len(text)}
