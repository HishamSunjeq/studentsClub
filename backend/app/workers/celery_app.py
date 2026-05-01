from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "studentsclub",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.process_upload",
        "app.workers.tasks.extract_questions",
        "app.workers.tasks.notify",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.process_upload.*": {"queue": "uploads"},
        "app.workers.tasks.extract_questions.*": {"queue": "ai"},
        "app.workers.tasks.notify.*": {"queue": "celery"},
    },
)
