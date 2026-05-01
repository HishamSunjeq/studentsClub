from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.extract_questions.run", bind=True, max_retries=3)
def run(self, upload_id: str, chunks: list[str]) -> dict:
    """Call AIProvider, persist QuestionSet draft. Implemented in Phase 4."""
    raise NotImplementedError
