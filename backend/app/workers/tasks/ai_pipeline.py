"""Celery entrypoint for the multi-stage orchestrator (Phase 4).

This task runs the entire canvas inside a single Celery job. Per-section
parallelism is provided via `asyncio.gather` inside the orchestrator —
no Celery `chord` is required at this stage, and telemetry parent
linkage stays clean.

`extract_questions.run` is kept as a thin shim that dispatches here so
external callers (the API endpoint) keep working without changes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from celery.exceptions import Reject, SoftTimeLimitExceeded

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.ai_pipeline.run",
    bind=True,
    max_retries=3,
)
def run(self, question_set_id: str, settings: dict[str, Any] | None = None) -> dict:  # type: ignore[return]
    try:
        return asyncio.run(_async_run(question_set_id, settings or {}))
    except _BudgetExceeded as be:
        asyncio.run(_mark_failed(question_set_id, str(be)))
        raise Reject(reason=str(be), requeue=False)
    except SoftTimeLimitExceeded:
        asyncio.run(_mark_failed(question_set_id, "Generation timed out"))
        raise
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(question_set_id, str(exc)))
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


class _BudgetExceeded(Exception):
    pass


async def _async_run(question_set_id: str, settings: dict[str, Any]) -> dict:
    from app.ai.budget import check_question_set_budget
    from app.ai.orchestrator.graph import run_generation_workflow
    from app.core.database import AsyncSessionLocal

    qs_uuid = uuid.UUID(question_set_id)

    async with AsyncSessionLocal() as db:
        budget = await check_question_set_budget(db, qs_uuid)
        if not budget.allowed:
            raise _BudgetExceeded(budget.reason or "QS budget exhausted")

    profile_id = None
    if settings.get("profile_id"):
        try:
            profile_id = uuid.UUID(str(settings["profile_id"]))
        except Exception:
            profile_id = None

    return await run_generation_workflow(
        qs_uuid,
        profile_id=profile_id,
        settings_overrides=settings,
    )


async def _mark_failed(question_set_id: str, message: str) -> None:
    from sqlalchemy import select

    from app.ai import events as ai_events
    from app.core.database import AsyncSessionLocal
    from app.models.question import QuestionSet, QuestionSetStatus

    upload_id = None
    async with AsyncSessionLocal() as db:
        async with db.begin():
            res = await db.execute(
                select(QuestionSet).where(QuestionSet.id == uuid.UUID(question_set_id))
            )
            qs = res.scalar_one_or_none()
            if qs is None:
                return
            qs.status = QuestionSetStatus.generation_failed
            qs.generation_error = message[:2000]
            upload_id = qs.upload_id

    # Notify any SSE subscribers so the stream closes cleanly on failure.
    if upload_id is not None:
        await ai_events.safe_publish(
            upload_id,
            {"type": "error", "question_set_id": question_set_id, "message": message[:500]},
        )
