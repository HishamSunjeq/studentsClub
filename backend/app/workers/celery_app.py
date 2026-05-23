"""Celery app configuration for StudentsClub workers.

Phase 1 hardening:
- `task_time_limit` / `task_soft_time_limit` to prevent runaway tasks.
- `task_acks_late` + `task_reject_on_worker_lost` so a worker crash re-queues
  the task instead of silently dropping it.
- `dead_letter` queue + global failure handler (in `app.workers.dlq`) that
  records terminal failures into a dedicated Redis list for operator triage.
- New `embeddings` queue (used by Phase 3 `embed_chunks.run`).
"""

from celery import Celery
from celery.signals import task_failure

from app.core.config import settings

celery_app = Celery(
    "studentsclub",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.process_upload",
        "app.workers.tasks.extract_questions",
        "app.workers.tasks.ai_pipeline",
        "app.workers.tasks.embed_chunks",
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
    # Phase 1 hardening.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=900,        # hard kill after 15 minutes
    task_soft_time_limit=840,   # raises SoftTimeLimitExceeded at 14 minutes
    result_extended=True,
    task_routes={
        "app.workers.tasks.process_upload.*": {"queue": "uploads"},
        "app.workers.tasks.extract_questions.*": {"queue": "ai"},
        "app.workers.tasks.ai_pipeline.*": {"queue": "ai"},
        "app.workers.tasks.embed_chunks.*": {"queue": "embeddings"},
        "app.workers.tasks.notify.*": {"queue": "celery"},
    },
)


@task_failure.connect
def _dlq_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, einfo=None, **_):
    """Push the final-failure record onto a Redis list for operator triage.

    Fires after Celery's retry policy has been exhausted. We deliberately use
    a fresh sync Redis client here (we're inside a signal handler that may run
    on the worker's IO thread) and swallow all errors — the DLQ is best-effort.
    """
    try:
        import json
        from datetime import datetime, timezone

        import redis as sync_redis

        payload = {
            "task_id": task_id,
            "task_name": getattr(sender, "name", None) if sender else None,
            "exception": f"{type(exception).__name__}: {exception}" if exception else None,
            "args": _safe_repr(args),
            "kwargs": _safe_repr(kwargs),
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        client = sync_redis.from_url(settings.celery_broker_url, decode_responses=True)
        client.lpush("celery:dead_letter", json.dumps(payload))
        # Keep last 1000 — older entries auto-trimmed.
        client.ltrim("celery:dead_letter", 0, 999)
        client.close()
    except Exception:
        # DLQ is observability — never let it kill the worker.
        pass


def _safe_repr(value, *, limit: int = 2000) -> str:
    try:
        s = repr(value)
    except Exception:
        s = "<unrepresentable>"
    return s if len(s) <= limit else s[:limit] + "...(truncated)"
