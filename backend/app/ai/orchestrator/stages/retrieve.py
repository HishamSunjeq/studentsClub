"""Stage 3: retrieve context for one section via HyDE + hybrid + rerank (Phase 4)."""

from __future__ import annotations

import logging
import uuid

from app.ai.events import safe_publish
from app.ai.orchestrator.profile import ResolvedProfile
from app.ai.orchestrator.schemas import RetrievedChunk, RetrievedContext, Section
from app.ai.rag.embedder.factory import get_embedder
from app.ai.rag.embedder.sparse import BM25SparseEncoder
from app.ai.rag.index import hybrid_search
from app.ai.rag.reranker.base import RerankCandidate
from app.ai.rag.reranker.factory import get_reranker
from app.ai.telemetry import run_logged

logger = logging.getLogger(__name__)


_HYDE_FALLBACK_PROMPT = (
    "Write a hypothetical 2-3 sentence answer or explanation for a study "
    "question that would be asked about the topic below. Focus on dense "
    "factual content, named entities, and key terms — this text will be "
    "used as an embedding query."
)


async def retrieve_for_section(
    *,
    profile: ResolvedProfile,
    section: Section,
    subject_id: uuid.UUID | None,
    upload_id: uuid.UUID | None,
    question_set_id: uuid.UUID,
    user_id: uuid.UUID | None,
    parent_run_id: uuid.UUID | None = None,
) -> RetrievedContext:
    query = (section.title or "") + "\n\n" + section.text[:2000]

    async def _degraded(reason: str) -> RetrievedContext:
        logger.warning(
            "retrieve: degraded section=%s reason=%s", section.position, reason
        )
        if upload_id is not None:
            await safe_publish(
                upload_id,
                {
                    "type": "retrieve.degraded",
                    "section_position": section.position,
                    "reason": reason,
                },
            )
        return RetrievedContext(
            section_position=section.position,
            query=query,
            hyde=hyde_text,
            degraded=True,
            degraded_reason=reason,
        )

    # 1. HyDE expansion (best-effort; falls back to the section text itself).
    hyde_text = await _hyde_expand(
        profile=profile,
        section=section,
        question_set_id=question_set_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
    )
    embed_query = hyde_text or query

    # 2. Dense + sparse encode the query.
    try:
        embedder = await get_embedder(
            credential_alias=profile.embedding_credential_alias,
            model=profile.embedding_model,
        )
        dense = (await embedder.embed([embed_query]))[0]
    except Exception:
        logger.exception("retrieve: dense embed failed for section=%s", section.position)
        return await _degraded("dense_embed_failed")

    sparse_encoder = BM25SparseEncoder()
    try:
        sparse = (await sparse_encoder.encode([embed_query]))[0]
    except Exception:
        logger.exception("retrieve: sparse encode failed for section=%s", section.position)
        from app.ai.rag.embedder.sparse import SparseVec

        sparse = SparseVec(indices=[], values=[])

    # 3. Hybrid search (RRF fusion server-side).
    try:
        hits = await hybrid_search(
            subject_id=subject_id,
            dense=dense,
            sparse=sparse,
            k=profile.top_k_retrieval,
            alpha=profile.hybrid_alpha,
            upload_id=None,  # cross-doc retrieval within the subject
        )
    except Exception:
        logger.exception("retrieve: hybrid_search failed for section=%s", section.position)
        return await _degraded("hybrid_search_failed")

    if not hits:
        return await _degraded("no_hits")

    # 4. Rerank top candidates.
    if profile.rerank_provider:
        try:
            reranker = await get_reranker(
                provider=profile.rerank_provider,
                credential_alias=profile.rerank_credential_alias,
                model=profile.rerank_model,
            )
            candidates = [
                RerankCandidate(id=str(h.chunk_id), text=h.text or "") for h in hits
            ]
            results = await reranker.rerank(
                query=embed_query, candidates=candidates, top_n=profile.top_n_rerank
            )
            ordered = [hits[r.index] for r in results]
            hits = ordered
        except Exception:
            logger.exception("retrieve: rerank failed; using hybrid order")
            hits = hits[: profile.top_n_rerank]
    else:
        hits = hits[: profile.top_n_rerank]

    chunks = [
        RetrievedChunk(
            chunk_id=h.chunk_id,
            upload_id=h.upload_id,
            section_title=h.section_title,
            text=h.text or "",
            score=h.score,
        )
        for h in hits
    ]
    return RetrievedContext(
        section_position=section.position,
        query=query,
        hyde=hyde_text,
        chunks=chunks,
    )


async def _hyde_expand(
    *,
    profile: ResolvedProfile,
    section: Section,
    question_set_id: uuid.UUID,
    user_id: uuid.UUID | None,
    parent_run_id: uuid.UUID | None,
) -> str | None:
    """Cheap LLM call (judge model) to produce a hypothetical passage to embed."""
    if profile.judge_provider == "mock":
        return None

    from app.ai.credentials import resolve as resolve_credential
    from app.ai.prompts_registry import get_active_prompt
    from app.core.database import AsyncSessionLocal

    # Resolve prompt + credential.
    try:
        prompt = (await get_active_prompt(profile.hyde_prompt_name)).content
    except Exception:
        prompt = _HYDE_FALLBACK_PROMPT

    try:
        async with AsyncSessionLocal() as db:
            cred = await resolve_credential(
                db,
                provider=profile.judge_provider,
                alias=profile.judge_credential_alias,
            )
    except Exception:
        return None

    user_msg = (
        f"Section title: {section.title or '(none)'}\n\nSection text:\n{section.text[:3000]}"
    )

    try:
        async with run_logged(
            task_name="orchestrator.hyde",
            provider=profile.judge_provider,
            model=profile.judge_model,
            credential_alias=profile.judge_credential_alias,
            question_set_id=question_set_id,
            user_id=user_id,
            parent_run_id=parent_run_id,
            meta={"stage": "hyde", "section": section.position},
        ) as tel:
            if profile.judge_provider == "anthropic":
                import anthropic

                client = anthropic.AsyncAnthropic(api_key=cred.api_key)
                resp = await client.messages.create(
                    model=profile.judge_model,
                    max_tokens=300,
                    system=prompt,
                    messages=[{"role": "user", "content": user_msg}],
                )
                out = resp.content[0].text if resp.content else ""
                tel.record_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
                return out.strip() or None

            if profile.judge_provider == "openai":
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=cred.api_key)
                resp = await client.chat.completions.create(
                    model=profile.judge_model,
                    max_tokens=300,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_msg},
                    ],
                )
                out = (resp.choices[0].message.content or "").strip()
                if resp.usage:
                    tel.record_tokens(resp.usage.prompt_tokens, resp.usage.completion_tokens)
                return out or None
    except Exception:
        logger.exception("HyDE failed")
        return None

    return None
