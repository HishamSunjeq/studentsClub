"""Per-user and per-QuestionSet token budget enforcement.

Checked **before** queueing a generation job. The check is best-effort
based on already-logged `ai_runs`; it cannot perfectly prevent a single
oversized job from blowing past the cap, but it prevents repeated abuse.

Configurable via:
- `settings.user_daily_token_budget` — sum of input+output tokens per user per 24h
- `settings.qs_max_tokens` — sum per QuestionSet (across all stages/retries)

Phase 2 extends this with per-credential monthly USD budgets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_run import AIRun


@dataclass
class BudgetStatus:
    allowed: bool
    reason: str | None = None
    user_tokens_today: int = 0
    user_daily_limit: int = 0
    qs_tokens: int = 0
    qs_limit: int = 0


async def check_user_daily_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> BudgetStatus:
    """True iff the user has tokens remaining for today (UTC rolling 24h)."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(
            func.coalesce(func.sum(AIRun.input_tokens + AIRun.output_tokens), 0)
        ).where(
            AIRun.user_id == user_id,
            AIRun.created_at >= since,
        )
    )
    used = int(result.scalar_one())
    limit = settings.user_daily_token_budget
    if used >= limit:
        return BudgetStatus(
            allowed=False,
            reason=(
                f"Daily token budget exhausted ({used:,} / {limit:,}). "
                "Resets 24 hours after your earliest call today."
            ),
            user_tokens_today=used,
            user_daily_limit=limit,
        )
    return BudgetStatus(
        allowed=True,
        user_tokens_today=used,
        user_daily_limit=limit,
    )


async def check_question_set_budget(
    db: AsyncSession,
    question_set_id: uuid.UUID,
) -> BudgetStatus:
    """True iff the QuestionSet hasn't already used more than its hard cap."""
    result = await db.execute(
        select(
            func.coalesce(func.sum(AIRun.input_tokens + AIRun.output_tokens), 0)
        ).where(AIRun.question_set_id == question_set_id)
    )
    used = int(result.scalar_one())
    limit = settings.qs_max_tokens
    if used >= limit:
        return BudgetStatus(
            allowed=False,
            reason=(
                f"QuestionSet token cap reached ({used:,} / {limit:,}). "
                "Open a new QuestionSet to continue."
            ),
            qs_tokens=used,
            qs_limit=limit,
        )
    return BudgetStatus(allowed=True, qs_tokens=used, qs_limit=limit)


async def check_combined(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    question_set_id: uuid.UUID | None = None,
) -> BudgetStatus:
    """Combined gate — both user and (optional) QS budget must be ok.

    Returns the user budget status when QS is absent, or the first failing one
    otherwise. Always returns the populated counters so callers can show
    'used X of Y' messages.
    """
    user_status = await check_user_daily_budget(db, user_id)
    if not user_status.allowed:
        return user_status
    if question_set_id is None:
        return user_status

    qs_status = await check_question_set_budget(db, question_set_id)
    qs_status.user_tokens_today = user_status.user_tokens_today
    qs_status.user_daily_limit = user_status.user_daily_limit
    return qs_status
