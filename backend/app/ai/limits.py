"""Redis token-bucket rate limiter for AI provider calls.

Buckets are keyed on `(provider, credential_alias, dimension)` where dimension
is e.g. `tpm` (tokens-per-minute) or `rpm` (requests-per-minute). Two buckets
typically apply to one call: one for requests, one for input tokens.

The algorithm uses two Redis keys per bucket:
- `{key}:tokens`  — current token count (float)
- `{key}:ts`      — last refill timestamp (epoch seconds, float)

Both are mutated atomically via Lua to avoid races between workers.

The caller treats rate-limit refusal as back-pressure, not failure:
the calling Celery task should re-queue itself with `apply_async(countdown=…)`
rather than fail. See `app/workers/tasks/extract_questions.py`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.ai.redis_client import get_redis
from app.core.config import settings


# Lua: atomically refill bucket and try to consume `cost` tokens.
# Returns {1, new_balance} on success, {0, seconds_until_refill_to_cost} on refusal.
_CONSUME_SCRIPT = """
local tokens_key = KEYS[1]
local ts_key = KEYS[2]
local capacity = tonumber(ARGV[1])
local refill_per_sec = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local tokens = tonumber(redis.call('GET', tokens_key))
local last_ts = tonumber(redis.call('GET', ts_key))

if tokens == nil then
  tokens = capacity
  last_ts = now
else
  local elapsed = math.max(0, now - last_ts)
  tokens = math.min(capacity, tokens + elapsed * refill_per_sec)
  last_ts = now
end

if tokens >= cost then
  tokens = tokens - cost
  redis.call('SET', tokens_key, tokens, 'EX', ttl)
  redis.call('SET', ts_key, last_ts, 'EX', ttl)
  return {1, tostring(tokens)}
else
  redis.call('SET', tokens_key, tokens, 'EX', ttl)
  redis.call('SET', ts_key, last_ts, 'EX', ttl)
  local needed = cost - tokens
  local wait = needed / refill_per_sec
  return {0, tostring(wait)}
end
"""


@dataclass(frozen=True)
class Bucket:
    """Single token bucket spec.

    `capacity` is the max tokens that can accumulate; `refill_per_sec` is the
    sustained rate. For "60 requests per minute" use capacity=60, refill=1.0.
    For "100k input tokens per minute" use capacity=100000, refill=100000/60.
    """

    name: str
    capacity: float
    refill_per_sec: float
    key: str  # full Redis key prefix, e.g. "ai:limits:anthropic:default:rpm"


@dataclass
class LimitResult:
    """Outcome of a `consume` attempt."""

    allowed: bool
    bucket: str
    retry_after_seconds: float  # 0 when allowed


class RateLimiter:
    """Token-bucket limiter over Redis using an atomic Lua script."""

    def __init__(self) -> None:
        self._script_sha: str | None = None

    async def _ensure_script(self) -> str:
        if self._script_sha is None:
            self._script_sha = await get_redis().script_load(_CONSUME_SCRIPT)
        return self._script_sha

    async def try_consume(self, bucket: Bucket, cost: float = 1.0) -> LimitResult:
        """Attempt to consume `cost` tokens from `bucket`. Non-blocking."""
        r = get_redis()
        sha = await self._ensure_script()
        now = time.time()
        ttl = max(60, int(bucket.capacity / max(bucket.refill_per_sec, 0.001)) * 2)
        result = await r.evalsha(
            sha,
            2,
            f"{bucket.key}:tokens",
            f"{bucket.key}:ts",
            bucket.capacity,
            bucket.refill_per_sec,
            now,
            cost,
            ttl,
        )
        allowed = int(result[0]) == 1
        wait_or_balance = float(result[1])
        return LimitResult(
            allowed=allowed,
            bucket=bucket.name,
            retry_after_seconds=0.0 if allowed else wait_or_balance,
        )


_limiter = RateLimiter()


def _bucket_key(provider: str, alias: str | None, dim: str) -> str:
    alias_part = alias or "default"
    return f"ai:limits:{provider}:{alias_part}:{dim}"


def buckets_for(provider: str, alias: str | None) -> list[Bucket]:
    """Return the bucket list applied to one provider call.

    Limits are read from settings. Defaults are generous enough to not block
    normal development traffic; tune via env vars in production.
    """
    rpm = getattr(settings, f"{provider}_rpm", None) or settings.ai_default_rpm
    tpm = getattr(settings, f"{provider}_tpm", None) or settings.ai_default_tpm

    return [
        Bucket(
            name=f"{provider}/rpm",
            capacity=float(rpm),
            refill_per_sec=float(rpm) / 60.0,
            key=_bucket_key(provider, alias, "rpm"),
        ),
        Bucket(
            name=f"{provider}/tpm",
            capacity=float(tpm),
            refill_per_sec=float(tpm) / 60.0,
            key=_bucket_key(provider, alias, "tpm"),
        ),
    ]


async def try_acquire(
    provider: str,
    *,
    estimated_input_tokens: int,
    credential_alias: str | None = None,
) -> LimitResult:
    """Try to acquire one request + estimated_input_tokens worth of tokens.

    Returns the FIRST failing bucket's result so the caller can wait the right
    amount. On success returns an allowed result for the "rpm" bucket.

    Strategy: try rpm bucket (cost=1), then tpm bucket (cost=estimated_input_tokens).
    Both must succeed; if either fails we report it and don't refund the other —
    refilling makes up for it within seconds and the simplicity is worth it.
    """
    rpm_bucket, tpm_bucket = buckets_for(provider, credential_alias)

    rpm_result = await _limiter.try_consume(rpm_bucket, cost=1.0)
    if not rpm_result.allowed:
        return rpm_result

    tpm_result = await _limiter.try_consume(tpm_bucket, cost=float(estimated_input_tokens))
    if not tpm_result.allowed:
        return tpm_result

    return rpm_result
