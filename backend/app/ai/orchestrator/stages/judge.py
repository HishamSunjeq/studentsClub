"""Stage 5: judge each candidate question on a rubric (Phase 4).

One LLM batch call per section's drafts. Returns 0-10 per question plus
a boolean `grounded` (does any cited chunk actually back the answer?).
Questions below `profile.judge_threshold` are marked `auto_rejected`.
"""

from __future__ import annotations

import json
import logging
import uuid

from app.ai.orchestrator.profile import ResolvedProfile
from app.ai.orchestrator.schemas import (
    CandidateQuestion,
    JudgedQuestion,
    RetrievedContext,
)
from app.ai.telemetry import run_logged

logger = logging.getLogger(__name__)


_JUDGE_FALLBACK_PROMPT = (
    "You are an exam-quality reviewer. For each question, score 0-10 on:\n"
    "- clarity (is the wording unambiguous?)\n"
    "- single-correct-answer (is exactly one option correct?)\n"
    "- distractor quality (are the wrong choices plausible?)\n"
    "- factual grounding (do the cited chunks support the correct answer?)\n\n"
    "Respond with STRICT JSON only — no prose, no code fences:\n"
    "{\n"
    '  "scores": [\n'
    '    {"index": int, "score": 0-10, "grounded": bool, "notes": "string"}\n'
    "  ]\n"
    "}"
)


async def judge_questions(
    *,
    profile: ResolvedProfile,
    candidates: list[CandidateQuestion],
    context_by_section: dict[int, RetrievedContext],
    candidate_section_positions: list[int] | None = None,
    question_set_id: uuid.UUID,
    user_id: uuid.UUID | None,
    parent_run_id: uuid.UUID | None = None,
) -> list[JudgedQuestion]:
    if not candidates:
        return []

    # Per-section degradation penalty: subtract from the final score for any
    # candidate produced from a section whose retrieval was degraded (no chunks,
    # embed failed, hybrid search failed, etc.). Floor at 0.
    degraded_positions = {
        pos for pos, ctx in context_by_section.items() if ctx.degraded
    }
    positions = candidate_section_positions or [-1] * len(candidates)

    def _apply_degradation_penalty(
        idx: int, score: float, notes: str | None
    ) -> tuple[float, bool, str | None]:
        if positions[idx] in degraded_positions:
            penalized = max(0.0, score - 2.0)
            extra = "retrieval degraded"
            new_notes = f"{notes}; {extra}" if notes else extra
            return penalized, penalized < profile.judge_threshold, new_notes
        return score, score < profile.judge_threshold, notes

    if profile.judge_provider == "mock":
        out: list[JudgedQuestion] = []
        for i, c in enumerate(candidates):
            score, rejected, notes = _apply_degradation_penalty(i, 8.0, None)
            out.append(
                JudgedQuestion(
                    question=c,
                    quality_score=score,
                    auto_rejected=rejected,
                    judge_notes=notes,
                )
            )
        return out

    # Build a chunk lookup so the judge sees what was cited.
    chunk_text_by_id: dict[uuid.UUID, str] = {}
    for ctx in context_by_section.values():
        for c in ctx.chunks:
            chunk_text_by_id[c.chunk_id] = c.text or ""

    try:
        prompt = await _get_prompt(profile.judge_prompt_name)
    except Exception:
        prompt = _JUDGE_FALLBACK_PROMPT

    user_msg = _build_user_message(candidates, chunk_text_by_id)

    try:
        async with run_logged(
            task_name="orchestrator.judge",
            provider=profile.judge_provider,
            model=profile.judge_model,
            credential_alias=profile.judge_credential_alias,
            question_set_id=question_set_id,
            user_id=user_id,
            parent_run_id=parent_run_id,
            meta={"stage": "judge", "n_candidates": len(candidates)},
        ) as tel:
            raw = await _call_llm(
                profile=profile,
                system=prompt,
                user=user_msg,
                tel=tel,
            )
    except Exception:
        logger.exception("judge LLM call failed; passing through with score=0")
        return [
            JudgedQuestion(question=c, quality_score=0.0, auto_rejected=True, judge_notes="judge failed")
            for c in candidates
        ]

    scores = _parse_scores(raw, len(candidates))
    judged: list[JudgedQuestion] = []
    for i, c in enumerate(candidates):
        s = scores.get(i)
        if s is None:
            judged.append(
                JudgedQuestion(
                    question=c,
                    quality_score=0.0,
                    auto_rejected=True,
                    judge_notes="no score",
                )
            )
            continue
        score = float(s.get("score", 0))
        grounded = bool(s.get("grounded", True))
        notes = str(s.get("notes") or "") or None
        score, rejected, notes = _apply_degradation_penalty(i, score, notes)
        if not grounded and len(c.source_chunk_ids) > 0:
            rejected = True
        judged.append(
            JudgedQuestion(
                question=c,
                quality_score=score,
                auto_rejected=rejected,
                judge_notes=notes,
            )
        )
    return judged


async def _get_prompt(name: str) -> str:
    from app.ai.prompts_registry import get_active_prompt

    return (await get_active_prompt(name)).content


def _build_user_message(
    candidates: list[CandidateQuestion],
    chunk_text_by_id: dict[uuid.UUID, str],
) -> str:
    lines = ["Score each of the following questions:"]
    for i, c in enumerate(candidates):
        lines.append(f"\n--- index={i} ---")
        lines.append(f"Question: {c.text}")
        lines.append("Choices:")
        for j, ch in enumerate(c.choices):
            lines.append(f"  {j}. {'[*]' if ch.is_correct else '[ ]'} {ch.text}")
        lines.append(f"Explanation: {c.explanation or '(none)'}")
        if c.source_chunk_ids:
            lines.append("Cited chunks:")
            for cid in c.source_chunk_ids:
                snippet = chunk_text_by_id.get(cid, "(chunk not found)")[:800]
                lines.append(f"  [{cid}]: {snippet}")
        else:
            lines.append("Cited chunks: NONE (penalize grounding)")
    return "\n".join(lines)


async def _call_llm(*, profile: ResolvedProfile, system: str, user: str, tel) -> str:
    from app.ai.credentials import resolve as resolve_credential
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        cred = await resolve_credential(
            db,
            provider=profile.judge_provider,
            alias=profile.judge_credential_alias,
        )

    if profile.judge_provider == "anthropic":
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=cred.api_key)
        resp = await client.messages.create(
            model=profile.judge_model,
            max_tokens=2500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text if resp.content else ""
        tel.record_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
        return text

    if profile.judge_provider == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=cred.api_key)
        resp = await client.chat.completions.create(
            model=profile.judge_model,
            max_tokens=2500,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or ""
        if resp.usage:
            tel.record_tokens(resp.usage.prompt_tokens, resp.usage.completion_tokens)
        return text

    raise ValueError(f"Unsupported judge provider: {profile.judge_provider}")


def _parse_scores(raw: str, n: int) -> dict[int, dict]:
    if not raw:
        return {}
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    data: dict | None = None
    try:
        data = json.loads(raw)
    except Exception:
        s, e = raw.find("{"), raw.rfind("}")
        if s >= 0 and e > s:
            try:
                data = json.loads(raw[s : e + 1])
            except Exception:
                data = None
    if not data:
        return {}
    out: dict[int, dict] = {}
    for entry in data.get("scores", []):
        try:
            idx = int(entry["index"])
        except Exception:
            continue
        if 0 <= idx < n:
            out[idx] = entry
    return out
