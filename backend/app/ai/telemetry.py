"""AI call telemetry.

Every provider invocation is wrapped in `run_logged(...)`. On success or
failure it inserts a single row into `ai_runs` with token usage, cost,
latency, and an optional parent run linkage for multi-stage pipelines.

Usage:

    async with run_logged(
        task_name="extract_questions.run",
        provider="anthropic",
        model="claude-opus-4-7",
        question_set_id=qs.id,
        user_id=user.id,
    ) as run:
        result = await provider.extract_questions(...)
        run.record_tokens(result.tokens_input, result.tokens_output, model=result.model)

If the block raises, the row is marked status=error with the truncated message.
If the block completes without calling `record_tokens` the run still lands with 0/0
tokens and 0 cost (used for cache-hit calls that should still be visible).
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from sqlalchemy import insert

from app.ai.pricing import estimate_cost_usd
from app.core.database import AsyncSessionLocal
from app.models.ai_run import AIRunStatus

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Mutable record updated inside the wrapped block; persisted on exit."""

    id: uuid.UUID
    task_name: str
    provider: str
    model: str
    credential_alias: str | None = None
    prompt_version_id: uuid.UUID | None = None
    parent_run_id: uuid.UUID | None = None
    question_set_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None

    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def record_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        model: str | None = None,
    ) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        if model is not None:
            self.model = model

    def mark_cache_hit(self) -> None:
        self.cache_hit = True

    def add_meta(self, **kwargs: Any) -> None:
        self.meta.update(kwargs)


@asynccontextmanager
async def run_logged(
    *,
    task_name: str,
    provider: str,
    model: str,
    credential_alias: str | None = None,
    prompt_version_id: uuid.UUID | None = None,
    parent_run_id: uuid.UUID | None = None,
    question_set_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> AsyncIterator[RunContext]:
    ctx = RunContext(
        id=uuid.uuid4(),
        task_name=task_name,
        provider=provider,
        model=model,
        credential_alias=credential_alias,
        prompt_version_id=prompt_version_id,
        parent_run_id=parent_run_id,
        question_set_id=question_set_id,
        user_id=user_id,
        meta=dict(meta or {}),
    )
    start = time.monotonic()
    status = AIRunStatus.ok
    error_message: str | None = None
    try:
        yield ctx
    except TimeoutError as exc:
        status = AIRunStatus.timeout
        error_message = str(exc)[:2000] or "TimeoutError"
        raise
    except Exception as exc:
        status = AIRunStatus.error
        error_message = f"{type(exc).__name__}: {exc}"[:2000]
        raise
    finally:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        cost = estimate_cost_usd(ctx.model, ctx.input_tokens, ctx.output_tokens)
        try:
            await _persist(
                ctx=ctx,
                latency_ms=elapsed_ms,
                cost_usd=cost,
                status=status,
                error=error_message,
            )
        except Exception:
            # Never let telemetry kill the request — log and swallow.
            logger.exception("Failed to persist ai_runs row id=%s", ctx.id)


async def _persist(
    *,
    ctx: RunContext,
    latency_ms: int,
    cost_usd: Any,
    status: AIRunStatus,
    error: str | None,
) -> None:
    from app.models.ai_run import AIRun

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(
                insert(AIRun).values(
                    id=ctx.id,
                    parent_run_id=ctx.parent_run_id,
                    question_set_id=ctx.question_set_id,
                    user_id=ctx.user_id,
                    task_name=ctx.task_name,
                    provider=ctx.provider,
                    model=ctx.model,
                    credential_alias=ctx.credential_alias,
                    prompt_version_id=ctx.prompt_version_id,
                    input_tokens=ctx.input_tokens,
                    output_tokens=ctx.output_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    cache_hit=ctx.cache_hit,
                    status=status,
                    error=error,
                    meta=ctx.meta,
                )
            )
