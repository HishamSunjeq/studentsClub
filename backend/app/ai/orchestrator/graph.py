"""End-to-end orchestrator: analyze -> segment -> retrieve -> generate
-> judge -> dedupe -> finalize (Phase 4).

Exposed as `run_generation_workflow(question_set_id)`. Called from the
new `ai_pipeline.run` Celery task; also callable directly in tests.

Section-parallel generation is bounded by `asyncio.Semaphore` derived
from `profile.section_concurrency`. All LLM calls within a single
workflow share a `parent_run_id` so the AIRunsPage can render the
canvas as one tree.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import events as ai_events
from app.ai.orchestrator.profile import ResolvedProfile, load_profile
from app.ai.orchestrator.schemas import (
    CandidateQuestion,
    JudgedQuestion,
    RetrievedContext,
    Section,
)
from app.ai.orchestrator.stages.analyze import analyze_document
from app.ai.orchestrator.stages.dedupe import dedupe_questions
from app.ai.orchestrator.stages.finalize import finalize_question_set
from app.ai.orchestrator.stages.generate_section import generate_section
from app.ai.orchestrator.stages.judge import judge_questions
from app.ai.orchestrator.stages.retrieve import retrieve_for_section
from app.ai.orchestrator.stages.segment import segment_document
from app.core.database import AsyncSessionLocal
from app.models.ai_model import AIModel
from app.models.question import QuestionSet, QuestionSetStatus
from app.models.upload import Upload

logger = logging.getLogger(__name__)


async def run_generation_workflow(
    question_set_id: uuid.UUID,
    *,
    profile_id: uuid.UUID | None = None,
    settings_overrides: dict | None = None,
) -> dict:
    """Run the full canvas. Caller is responsible for top-level error
    handling (the Celery task wraps this in `_mark_failed`).
    """
    parent_run_id = uuid.uuid4()  # acts as the canvas's run group id

    # 1. Load QS + upload + profile.
    async with AsyncSessionLocal() as db:
        qs_res = await db.execute(select(QuestionSet).where(QuestionSet.id == question_set_id))
        qs = qs_res.scalar_one_or_none()
        if qs is None:
            raise ValueError(f"QuestionSet {question_set_id} not found")
        up_res = await db.execute(select(Upload).where(Upload.id == qs.upload_id))
        upload = up_res.scalar_one()
        if not upload.extracted_text:
            raise ValueError(f"Upload {upload.id} has no extracted_text")

        profile = await load_profile(db, subject_id=qs.subject_id, profile_id=profile_id)

        if settings_overrides:
            profile = await _apply_overrides(db, profile, settings_overrides)

    user_id = qs.created_by
    subject_id = qs.subject_id
    upload_id = upload.id
    text = upload.extracted_text

    # Best-effort: prompt version id for telemetry/replay.
    prompt_version_id = await _resolve_prompt_version(profile.extraction_prompt_name)

    await ai_events.safe_publish(upload_id, {"type": "analyze.started"})

    # 2. Analyze.
    analysis = await analyze_document(
        profile=profile,
        text=text,
        question_set_id=question_set_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
    )
    if profile.target_count:
        analysis.suggested_total_questions = min(
            analysis.suggested_total_questions, profile.target_count
        )

    await ai_events.safe_publish(
        upload_id,
        {
            "type": "analyze.completed",
            "doc_type": analysis.doc_type,
            "language": analysis.language,
            "target_questions": analysis.suggested_total_questions,
        },
    )

    # 3. Segment.
    sections = segment_document(text, analysis)
    if not sections:
        raise ValueError("Segmentation produced no sections")

    await ai_events.safe_publish(
        upload_id,
        {"type": "segment.completed", "sections": len(sections)},
    )

    # 4. Per-section: retrieve -> generate, bounded by semaphore.
    sem = asyncio.Semaphore(max(1, profile.section_concurrency))

    async def _section_pipeline(section: Section) -> tuple[Section, RetrievedContext, list[CandidateQuestion]]:
        async with sem:
            await ai_events.safe_publish(
                upload_id,
                {
                    "type": "generate.section.started",
                    "section": section.position,
                    "title": section.title,
                },
            )
            ctx = await retrieve_for_section(
                profile=profile,
                section=section,
                subject_id=subject_id,
                upload_id=upload_id,
                question_set_id=question_set_id,
                user_id=user_id,
                parent_run_id=parent_run_id,
            )
            await ai_events.safe_publish(
                upload_id,
                {
                    "type": "retrieve.completed",
                    "section": section.position,
                    "chunks": len(ctx.chunks),
                },
            )
            draft = await generate_section(
                profile=profile,
                section=section,
                context=ctx,
                question_set_id=question_set_id,
                user_id=user_id,
                parent_run_id=parent_run_id,
            )
            await ai_events.safe_publish(
                upload_id,
                {
                    "type": "generate.section.completed",
                    "section": section.position,
                    "questions": len(draft.questions),
                },
            )
            return section, ctx, draft.questions

    results = await asyncio.gather(*[_section_pipeline(s) for s in sections])

    all_candidates: list[CandidateQuestion] = []
    candidate_section_positions: list[int] = []
    context_by_section: dict[int, RetrievedContext] = {}
    for section, ctx, qs_list in results:
        context_by_section[section.position] = ctx
        all_candidates.extend(qs_list)
        candidate_section_positions.extend([section.position] * len(qs_list))

    if not all_candidates:
        await ai_events.safe_publish(upload_id, {"type": "generate.completed", "kept": 0})
        return await _finalize_empty(question_set_id, profile.extraction_model)

    # 5. Judge.
    judged = await judge_questions(
        profile=profile,
        candidates=all_candidates,
        candidate_section_positions=candidate_section_positions,
        context_by_section=context_by_section,
        question_set_id=question_set_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
    )
    rejected = sum(1 for j in judged if j.auto_rejected)
    await ai_events.safe_publish(
        upload_id,
        {
            "type": "judge.completed",
            "scored": len(judged),
            "auto_rejected": rejected,
        },
    )

    # 6. Dedupe against published bank.
    deduped, dropped = await dedupe_questions(
        profile=profile, judged=judged, subject_id=subject_id
    )
    await ai_events.safe_publish(
        upload_id,
        {
            "type": "dedupe.completed",
            "kept": sum(1 for j in deduped if not j.auto_rejected),
            "dropped": dropped,
        },
    )

    # 7. Finalize.
    total_tokens = 0  # telemetry is recorded per stage; we don't double-count here.
    inserted = await finalize_question_set(
        question_set_id=question_set_id,
        judged=deduped,
        extraction_model=profile.extraction_model,
        prompt_version_id=prompt_version_id,
        total_tokens_used=total_tokens,
    )

    await ai_events.safe_publish(
        upload_id,
        {
            "type": "generate.completed",
            "inserted": inserted,
            "auto_rejected": rejected,
            "dropped": dropped,
        },
    )

    return {
        "question_set_id": str(question_set_id),
        "questions_inserted": inserted,
        "auto_rejected": rejected,
        "dedup_dropped": dropped,
        "model": profile.extraction_model,
        "profile": profile.name,
    }


async def _apply_overrides(
    db: AsyncSession, profile: ResolvedProfile, overrides: dict
) -> ResolvedProfile:
    """Whitelist override knobs from the generate payload.

    `extraction_model_id` resolves an `ai_models` row and patches
    provider + model + (optional) credential alias *together*, so picking
    an OpenAI model never leaves an Anthropic provider string behind.
    The legacy `model` string key is still honored for back-compat.
    """
    from dataclasses import replace

    patches: dict = {}

    if overrides.get("count"):
        try:
            patches["target_count"] = int(overrides["count"])
        except (TypeError, ValueError):
            pass

    alias = overrides.get("extraction_credential_alias") or overrides.get(
        "credential_alias"
    )
    if alias:
        patches["extraction_credential_alias"] = alias

    mid = overrides.get("extraction_model_id")
    if mid:
        try:
            mid_uuid = mid if isinstance(mid, uuid.UUID) else uuid.UUID(str(mid))
        except (TypeError, ValueError):
            mid_uuid = None
        if mid_uuid is not None:
            res = await db.execute(select(AIModel).where(AIModel.id == mid_uuid))
            model = res.scalar_one_or_none()
            if model is not None:
                patches["extraction_provider"] = model.provider
                patches["extraction_model"] = model.model_id
    elif overrides.get("model"):
        patches["extraction_model"] = overrides["model"]

    if not patches:
        return profile
    return replace(profile, **patches)


async def _resolve_prompt_version(prompt_name: str) -> uuid.UUID | None:
    try:
        from app.ai.prompts_registry import get_active_prompt

        record = await get_active_prompt(prompt_name)
        return record.id
    except Exception:
        return None


async def _finalize_empty(question_set_id: uuid.UUID, model: str) -> dict:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            res = await db.execute(
                select(QuestionSet).where(QuestionSet.id == question_set_id)
            )
            qs = res.scalar_one()
            qs.status = QuestionSetStatus.draft
            qs.ai_model = model
    return {
        "question_set_id": str(question_set_id),
        "questions_inserted": 0,
        "model": model,
    }
