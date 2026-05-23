"""Admin AI metrics aggregation over `ai_runs` (Phase 6).

Powers the dashboard: daily cost/token series, latency percentiles, cache
hit rate, and cost breakdowns by provider / model / credential. A single
endpoint so the dashboard makes one request per range.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import Numeric, cast, func, select

from app.api.deps import AdminUser, DBSession
from app.models.ai_run import AIRun
from app.schemas.admin import AIMetricsResponse, MetricPoint, MetricsBreakdownRow

router = APIRouter()


async def _breakdown(db, column, since) -> list[MetricsBreakdownRow]:
    q = (
        select(
            column,
            func.coalesce(func.sum(AIRun.cost_usd), 0),
            func.count(),
        )
        .where(AIRun.created_at >= since)
        .group_by(column)
        .order_by(func.sum(AIRun.cost_usd).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        MetricsBreakdownRow(key=str(k) if k is not None else "(none)", cost_usd=c, calls=n)
        for k, c, n in rows
    ]


@router.get("", response_model=AIMetricsResponse)
async def ai_metrics(
    db: DBSession,
    _: AdminUser,
    range_days: int = Query(default=30, ge=1, le=365, alias="range"),
) -> AIMetricsResponse:
    since = datetime.now(UTC) - timedelta(days=range_days)

    totals_q = select(
        func.coalesce(func.sum(AIRun.cost_usd), 0),
        func.count(),
        func.coalesce(func.sum(AIRun.input_tokens), 0),
        func.coalesce(func.sum(AIRun.output_tokens), 0),
        func.coalesce(func.sum(cast(AIRun.cache_hit, Numeric)), 0),
    ).where(AIRun.created_at >= since)
    total_cost, total_calls, total_in, total_out, cache_hits = (
        await db.execute(totals_q)
    ).one()

    cache_hit_rate = float(cache_hits) / total_calls if total_calls else 0.0

    # Latency percentiles (Postgres percentile_cont over non-null latencies).
    pct_q = select(
        func.percentile_cont(0.5).within_group(AIRun.latency_ms.asc()),
        func.percentile_cont(0.95).within_group(AIRun.latency_ms.asc()),
    ).where(AIRun.created_at >= since, AIRun.latency_ms.isnot(None))
    p50, p95 = (await db.execute(pct_q)).one()

    # Daily series.
    day_col = func.date_trunc("day", AIRun.created_at)
    daily_q = (
        select(
            day_col.label("day"),
            func.coalesce(func.sum(AIRun.cost_usd), 0),
            func.coalesce(func.sum(AIRun.input_tokens), 0),
            func.coalesce(func.sum(AIRun.output_tokens), 0),
            func.count(),
            func.coalesce(func.sum(cast(AIRun.cache_hit, Numeric)), 0),
        )
        .where(AIRun.created_at >= since)
        .group_by(day_col)
        .order_by(day_col.asc())
    )
    daily = [
        MetricPoint(
            day=day.date().isoformat() if hasattr(day, "date") else str(day),
            cost_usd=cost,
            input_tokens=int(tin),
            output_tokens=int(tout),
            calls=int(calls),
            cache_hits=int(ch),
        )
        for day, cost, tin, tout, calls, ch in (await db.execute(daily_q)).all()
    ]

    return AIMetricsResponse(
        range_days=range_days,
        total_cost_usd=total_cost,
        total_calls=total_calls,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        cache_hit_rate=cache_hit_rate,
        p50_latency_ms=int(p50) if p50 is not None else None,
        p95_latency_ms=int(p95) if p95 is not None else None,
        daily=daily,
        by_provider=await _breakdown(db, AIRun.provider, since),
        by_model=await _breakdown(db, AIRun.model, since),
        by_credential=await _breakdown(db, AIRun.credential_alias, since),
    )
