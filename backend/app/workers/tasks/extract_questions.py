"""Legacy `extract_questions.run` task — thin compatibility shim (Phase 4).

The original single-LLM-call generation pipeline is now superseded by
`app.workers.tasks.ai_pipeline.run`, which runs the multi-stage
orchestrator (analyze -> segment -> per-section retrieve + generate ->
judge -> dedupe -> finalize) with hybrid retrieval + reranking.

This shim is preserved so any caller still referencing the old task
name (`app.workers.tasks.extract_questions.run`) keeps working — it
just forwards the same arguments to the orchestrator task.
"""

from __future__ import annotations

import logging
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.extract_questions.run")
def run(question_set_id: str, settings: dict[str, Any] | None = None) -> dict:
    """Forwards to the Phase 4 orchestrator task."""
    from app.workers.tasks.ai_pipeline import run as pipeline_run

    async_result = pipeline_run.apply_async(
        args=[question_set_id, settings or {}], queue="ai"
    )
    return {
        "forwarded_to": "ai_pipeline.run",
        "task_id": async_result.id,
        "question_set_id": question_set_id,
    }
