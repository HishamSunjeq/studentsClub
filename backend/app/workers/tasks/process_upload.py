from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_upload.run", bind=True, max_retries=3)
def run(self, upload_id: str) -> dict:
    """Download file from S3, parse text, enqueue extract_questions. Implemented in Phase 4."""
    raise NotImplementedError
