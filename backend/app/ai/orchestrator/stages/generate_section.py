"""Stage 4: generate questions for one section with retrieved context (Phase 4).

The prompt requires the model to emit `source_chunk_ids` from the
context window we supply. We embed the chunk IDs in the prompt and
parse them back from the JSON response, then filter to IDs we actually
provided (so the model can't hallucinate UUIDs).
"""

from __future__ import annotations

import json
import logging
import re
import uuid

from app.ai.base import ChoiceDraft
from app.ai.orchestrator.profile import ResolvedProfile
from app.ai.orchestrator.schemas import (
    CandidateQuestion,
    RetrievedContext,
    Section,
    SectionDraft,
)
from app.ai.telemetry import run_logged

logger = logging.getLogger(__name__)


_GENERATION_SYSTEM = (
    "You are an expert exam-question author. Create multiple-choice questions "
    "(4 choices, exactly one correct) grounded STRICTLY in the supplied "
    "section text and the retrieved context chunks.\n\n"
    "Rules:\n"
    "- Each question MUST cite at least one context chunk via its `chunk_id`.\n"
    "- Distractors must be plausible and span the section's concepts.\n"
    "- Vary difficulty according to the requested mix.\n"
    "- Respond with STRICT JSON only, no prose, no code fences.\n\n"
    "Schema:\n"
    "{\n"
    '  "questions": [\n'
    "    {\n"
    '      "text": "string",\n'
    '      "choices": [{"text": "string", "is_correct": bool}, ...]   (exactly 4),\n'
    '      "explanation": "string",\n'
    '      "difficulty": "easy" | "medium" | "hard",\n'
    '      "source_chunk_ids": ["uuid", ...]      (>=1; MUST come from the provided context),\n'
    '      "source_excerpt": "string (short verbatim quote)"\n'
    "    }, ...\n"
    "  ]\n"
    "}"
)


async def generate_section(
    *,
    profile: ResolvedProfile,
    section: Section,
    context: RetrievedContext,
    question_set_id: uuid.UUID,
    user_id: uuid.UUID | None,
    parent_run_id: uuid.UUID | None = None,
) -> SectionDraft:
    if profile.extraction_provider == "mock":
        return _mock_section_draft(section)

    allowed_ids = {c.chunk_id for c in context.chunks}
    user_msg = _build_user_message(section, context, profile)

    async with run_logged(
        task_name="orchestrator.generate_section",
        provider=profile.extraction_provider,
        model=profile.extraction_model,
        credential_alias=profile.extraction_credential_alias,
        question_set_id=question_set_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
        meta={
            "stage": "generate_section",
            "section": section.position,
            "target_questions": section.target_questions,
            "context_chunks": len(context.chunks),
        },
    ) as tel:
        raw = await _call_llm(
            profile=profile,
            system=_GENERATION_SYSTEM,
            user=user_msg,
            tel=tel,
        )

    parsed = _parse_response(raw, allowed_ids)
    return SectionDraft(
        section_position=section.position,
        questions=parsed,
        tokens_input=0,
        tokens_output=0,
        model=profile.extraction_model,
    )


def _build_user_message(
    section: Section, context: RetrievedContext, profile: ResolvedProfile
) -> str:
    lines = [
        f"Section title: {section.title or '(none)'}",
        f"Target question count: {section.target_questions}",
        f"Difficulty mix: {json.dumps(profile.difficulty_mix)}",
        "",
        "Section text:",
        section.text,
        "",
        "Retrieved context (each chunk is keyed by `chunk_id`; cite by UUID):",
    ]
    if not context.chunks:
        lines.append("(no additional context — base questions on section text alone)")
    else:
        for c in context.chunks:
            snippet = (c.text or "")[:1200]
            lines.append(
                f"[chunk_id={c.chunk_id}] section={c.section_title or '(none)'}\n{snippet}"
            )
            lines.append("")
    return "\n".join(lines)


async def _call_llm(*, profile: ResolvedProfile, system: str, user: str, tel) -> str:
    from app.ai.credentials import resolve as resolve_credential
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        cred = await resolve_credential(
            db,
            provider=profile.extraction_provider,
            alias=profile.extraction_credential_alias,
        )

    if profile.extraction_provider == "anthropic":
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=cred.api_key)
        resp = await client.messages.create(
            model=profile.extraction_model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text if resp.content else ""
        tel.record_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
        return text

    if profile.extraction_provider == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=cred.api_key)
        resp = await client.chat.completions.create(
            model=profile.extraction_model,
            max_tokens=4000,
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


_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)


def _parse_response(raw: str, allowed_ids: set[uuid.UUID]) -> list[CandidateQuestion]:
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()

    data: dict | None = None
    try:
        data = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
            except Exception:
                data = None

    if not data:
        logger.warning("generate_section: unparseable response raw=%r", raw[:300])
        return []

    out: list[CandidateQuestion] = []
    for q in data.get("questions", []):
        text = (q.get("text") or "").strip()
        if not text:
            continue
        choices_raw = q.get("choices") or []
        choices = []
        for c in choices_raw:
            ct = (c.get("text") or "").strip()
            if not ct:
                continue
            choices.append(ChoiceDraft(text=ct, is_correct=bool(c.get("is_correct"))))
        if len(choices) < 2:
            continue
        if not any(c.is_correct for c in choices):
            continue

        # Filter source_chunk_ids to ones we actually supplied — drops hallucinated UUIDs.
        cited: list[uuid.UUID] = []
        for raw_id in q.get("source_chunk_ids") or []:
            try:
                u = uuid.UUID(str(raw_id))
            except Exception:
                continue
            if u in allowed_ids:
                cited.append(u)
        # Also accept UUIDs found inline in text/explanation if model put them there.
        if not cited:
            for s in (q.get("explanation") or "", q.get("source_excerpt") or "", text):
                for m in _UUID_RE.findall(s):
                    try:
                        u = uuid.UUID(m)
                    except Exception:
                        continue
                    if u in allowed_ids and u not in cited:
                        cited.append(u)

        difficulty = q.get("difficulty") or "medium"
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"

        out.append(
            CandidateQuestion(
                text=text,
                choices=choices,
                explanation=(q.get("explanation") or None),
                difficulty=difficulty,  # type: ignore[arg-type]
                source_chunk_ids=cited,
                source_excerpt=(q.get("source_excerpt") or None),
            )
        )
    return out


def _mock_section_draft(section: Section) -> SectionDraft:
    """Deterministic stub used in tests."""
    qs: list[CandidateQuestion] = []
    for i in range(section.target_questions):
        qs.append(
            CandidateQuestion(
                text=f"[mock] question {i + 1} for section {section.position}",
                choices=[
                    ChoiceDraft(text="A", is_correct=True),
                    ChoiceDraft(text="B", is_correct=False),
                    ChoiceDraft(text="C", is_correct=False),
                    ChoiceDraft(text="D", is_correct=False),
                ],
                explanation="mock",
                difficulty="medium",
                source_chunk_ids=[],
            )
        )
    return SectionDraft(
        section_position=section.position,
        questions=qs,
        model="mock",
    )
