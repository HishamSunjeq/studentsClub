from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.notify.send")
def send(user_id: str, event: str, payload: dict) -> None:
    """Send in-app/email notification. Implemented in Phase 4."""
    raise NotImplementedError
