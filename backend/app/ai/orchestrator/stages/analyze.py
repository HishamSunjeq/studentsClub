"""Stage 1: analyze the document — doc_type, language, suggested count (Phase 4).

A single LLM call summarizes the document into structured metadata used
by later stages (target_count, language hint, sectioning guidance). We
ask for strict JSON so we can parse without a schema validator dance.
"""

from __future__ import annotations

import json
import logging
import uuid

from app.ai.orchestrator.profile import ResolvedProfile
from app.ai.orchestrator.schemas import DocumentAnalysis
from app.ai.telemetry import run_logged

logger = logging.getLogger(__name__)


_ANALYZE_PROMPT = (
    "You are analyzing a study document. Respond with STRICT JSON only — no "
    "prose, no code fences. Schema:\n"
    "{\n"
    '  "doc_type": "study_material" | "exam_paper" | "lecture_notes" | "textbook" | "other",\n'
    '  "language": "en" | "ar" | "fr" | ... (ISO-639-1),\n'
    '  "suggested_total_questions": int (5-50),\n'
    '  "section_outline": [string, ...]   (5-15 short section labels)\n'
    "}"
)


async def analyze_document(
    *,
    profile: ResolvedProfile,
    text: str,
    question_set_id: uuid.UUID,
    user_id: uuid.UUID | None,
    parent_run_id: uuid.UUID | None = None,
) -> DocumentAnalysis:
    # Truncate to a reasonable preview window — analyze doesn't need full text.
    preview = text[:18000]

    if profile.extraction_provider == "mock":
        return DocumentAnalysis(suggested_total_questions=profile.target_count)

    async with run_logged(
        task_name="orchestrator.analyze",
        provider=profile.extraction_provider,
        model=profile.extraction_model,
        credential_alias=profile.extraction_credential_alias,
        question_set_id=question_set_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
        meta={"stage": "analyze"},
    ) as tel:
        raw = await _call_llm(
            profile=profile,
            system=_ANALYZE_PROMPT,
            user=preview,
            max_tokens=600,
            tel=tel,
        )

    data = _safe_json(raw)
    return DocumentAnalysis(
        doc_type=str(data.get("doc_type") or "study_material"),
        language=data.get("language"),
        suggested_total_questions=_clamp_int(
            data.get("suggested_total_questions"), 5, 50, profile.target_count
        ),
        section_outline=[str(s) for s in (data.get("section_outline") or []) if s],
    )


async def _call_llm(*, profile: ResolvedProfile, system: str, user: str, max_tokens: int, tel) -> str:
    from app.ai.credentials import resolve as resolve_credential
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        cred = await resolve_credential(
            db,
            provider=profile.extraction_provider,
            alias=profile.extraction_credential_alias,
        )
    api_key = cred.api_key

    if profile.extraction_provider == "anthropic":
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=profile.extraction_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text if resp.content else ""
        tel.record_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
        return text

    if profile.extraction_provider == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model=profile.extraction_model,
            max_tokens=max_tokens,
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

    raise ValueError(f"Unsupported extraction provider: {profile.extraction_provider}")


def _safe_json(raw: str) -> dict:
    if not raw:
        return {}
    raw = raw.strip()
    # Strip code fences if the model ignored "no fences".
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    try:
        return json.loads(raw)
    except Exception:
        # Try to locate the first balanced JSON object.
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except Exception:
                pass
    logger.warning("analyze: could not parse JSON; raw=%r", raw[:200])
    return {}


def _clamp_int(v, lo: int, hi: int, default: int) -> int:
    try:
        n = int(v)
    except Exception:
        return default
    return max(lo, min(hi, n))
