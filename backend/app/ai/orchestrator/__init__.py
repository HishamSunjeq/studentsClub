"""Multi-stage AI generation orchestrator (Phase 4).

Pipeline:
  analyze -> segment -> (per section: retrieve [HyDE + hybrid + rerank]
  -> generate) -> judge -> dedupe -> finalize.

Each stage is a small async function in `stages/` that returns its
output. `graph.run_generation_workflow(question_set_id)` wires them
together with `asyncio.gather` for per-section parallelism.

We deliberately keep the canvas inside one Celery task: telemetry
parent linkage stays clean, and we don't pay JSON serialization on
the intermediate drafts. Section-parallel concurrency is enforced
by `asyncio.Semaphore(...)` derived from the profile.
"""

from app.ai.orchestrator.graph import run_generation_workflow

__all__ = ["run_generation_workflow"]
