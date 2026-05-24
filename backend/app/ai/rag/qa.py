"""Subject Q&A: grounded answer over the subject's hybrid index (Phase 7).

Mirrors the generation-time retrieval pipeline (HyDE → hybrid → rerank) but
ends in a free-form answer instead of question generation. The answer prompt
(`subject_qa.system`) requires `[#chunk_id]` citation markers; we parse those
back into resolved chunk references for the UI.

Falls back gracefully when no live provider is configured (dev / tests): it
still retrieves and returns the top excerpts so the feature is exercisable
without API keys.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.credentials import resolve as resolve_credential
from app.ai.events import safe_publish_chat
from app.ai.orchestrator.profile import ResolvedProfile, load_profile
from app.ai.prompts_registry import get_active_prompt
from app.ai.rag.embedder.factory import get_embedder
from app.ai.rag.embedder.sparse import BM25SparseEncoder, SparseVec
from app.ai.rag.index import HybridHit, hybrid_search
from app.ai.rag.reranker.base import RerankCandidate
from app.ai.rag.reranker.factory import get_reranker
from app.ai.telemetry import run_logged

logger = logging.getLogger(__name__)

_QA_FALLBACK_PROMPT = (
    "You are a study assistant for a university subject. Answer the question "
    "using ONLY the supplied source excerpts. Cite each claim with a [#chunk_id] "
    "marker. If the excerpts don't contain the answer, say so plainly."
)

_HISTORY_TURNS = 6
_CITATION_RE = re.compile(r"\[#([0-9a-fA-F-]{8,})\]")


@dataclass
class Citation:
    chunk_id: uuid.UUID
    upload_id: uuid.UUID | None
    section_title: str | None
    text: str


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    tokens: int = 0
    model: str | None = None

    def citations_json(self) -> list[dict]:
        return [
            {
                "chunk_id": str(c.chunk_id),
                "upload_id": str(c.upload_id) if c.upload_id else None,
                "section_title": c.section_title,
                "text": c.text,
            }
            for c in self.citations
        ]


async def answer_subject_question(
    db: AsyncSession,
    *,
    subject_id: uuid.UUID,
    query: str,
    history: list[dict[str, str]] | None = None,
    user_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
) -> AnswerResult:
    profile = await load_profile(db, subject_id=subject_id)
    history = history or []

    if session_id is not None:
        await safe_publish_chat(session_id, {"type": "retrieve.started"})

    hits = await _retrieve(db, profile=profile, subject_id=subject_id, query=query)

    if session_id is not None:
        await safe_publish_chat(
            session_id, {"type": "retrieve.completed", "hits": len(hits)}
        )

    if not hits:
        answer = (
            "I couldn't find anything in this subject's material to answer "
            "that. Try rephrasing, or upload more notes for this subject."
        )
        if session_id is not None:
            await safe_publish_chat(session_id, {"type": "token", "delta": answer})
            await safe_publish_chat(
                session_id, {"type": "done", "citations": []}
            )
        return AnswerResult(answer=answer)

    context = "\n\n".join(
        f"[#{h.chunk_id}] ({h.section_title or 'untitled'})\n{h.text or ''}"
        for h in hits
    )

    try:
        system_prompt = (await get_active_prompt("subject_qa.system")).content
    except Exception:
        system_prompt = _QA_FALLBACK_PROMPT

    provider = profile.extraction_provider
    model = profile.extraction_model

    # Dev / test fallback: no live provider → return the strongest excerpt.
    if provider not in ("anthropic", "openai"):
        top = hits[0]
        answer = (
            f"Based on the subject material:\n\n{(top.text or '').strip()[:600]}"
        )
        citations = _citations_from_hits(hits[:3])
        if session_id is not None:
            await _stream_mock(session_id, answer, citations)
        return AnswerResult(answer=answer, citations=citations, model=model)

    messages = _build_messages(history=history, context=context, query=query)

    answer_text, tokens = await _complete(
        db,
        provider=provider,
        model=model,
        credential_alias=profile.extraction_credential_alias,
        system_prompt=system_prompt,
        messages=messages,
        user_id=user_id,
        session_id=session_id,
    )

    citations = _resolve_citations(answer_text, hits)
    if session_id is not None:
        await safe_publish_chat(
            session_id,
            {
                "type": "done",
                "citations": [
                    {
                        "chunk_id": str(c.chunk_id),
                        "upload_id": str(c.upload_id) if c.upload_id else None,
                        "section_title": c.section_title,
                        "text": c.text,
                    }
                    for c in citations
                ],
            },
        )
    return AnswerResult(
        answer=answer_text.strip(),
        citations=citations,
        tokens=tokens,
        model=model,
    )


async def _stream_mock(
    session_id: uuid.UUID, answer: str, citations: list[Citation]
) -> None:
    """Emit the fallback answer as a few token chunks so the SSE UX is exercisable
    without a live provider key."""
    import asyncio

    chunk_size = max(1, len(answer) // 12)
    for i in range(0, len(answer), chunk_size):
        await safe_publish_chat(
            session_id, {"type": "token", "delta": answer[i : i + chunk_size]}
        )
        await asyncio.sleep(0.05)
    await safe_publish_chat(
        session_id,
        {
            "type": "done",
            "citations": [
                {
                    "chunk_id": str(c.chunk_id),
                    "upload_id": str(c.upload_id) if c.upload_id else None,
                    "section_title": c.section_title,
                    "text": c.text,
                }
                for c in citations
            ],
        },
    )


async def _retrieve(
    db: AsyncSession,
    *,
    profile: ResolvedProfile,
    subject_id: uuid.UUID,
    query: str,
) -> list[HybridHit]:
    embed_query = await _hyde(db, profile=profile, query=query) or query

    try:
        embedder = await get_embedder(
            credential_alias=profile.embedding_credential_alias,
            model=profile.embedding_model,
        )
        dense = (await embedder.embed([embed_query]))[0]
    except Exception:
        logger.exception("qa: dense embed failed")
        return []

    try:
        sparse = (await BM25SparseEncoder().encode([embed_query]))[0]
    except Exception:
        sparse = SparseVec(indices=[], values=[])

    try:
        hits = await hybrid_search(
            subject_id=subject_id,
            dense=dense,
            sparse=sparse,
            k=profile.top_k_retrieval,
            alpha=profile.hybrid_alpha,
        )
    except Exception:
        logger.exception("qa: hybrid_search failed")
        return []

    if not hits:
        return []

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
            return [hits[r.index] for r in results]
        except Exception:
            logger.exception("qa: rerank failed; using hybrid order")

    return hits[: profile.top_n_rerank]


async def _hyde(
    db: AsyncSession, *, profile: ResolvedProfile, query: str
) -> str | None:
    """Hypothetical-answer expansion to embed instead of the terse query."""
    if profile.judge_provider not in ("anthropic", "openai"):
        return None
    try:
        prompt = (await get_active_prompt(profile.hyde_prompt_name)).content
    except Exception:
        return None
    try:
        cred = await resolve_credential(
            db, provider=profile.judge_provider, alias=profile.judge_credential_alias
        )
    except Exception:
        return None

    try:
        if profile.judge_provider == "anthropic":
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=cred.api_key)
            resp = await client.messages.create(
                model=profile.judge_model,
                max_tokens=256,
                system=prompt,
                messages=[{"role": "user", "content": query}],
            )
            return (resp.content[0].text if resp.content else "").strip() or None

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=cred.api_key)
        resp = await client.chat.completions.create(
            model=profile.judge_model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:
        logger.exception("qa: HyDE failed")
        return None


def _build_messages(
    *, history: list[dict[str, str]], context: str, query: str
) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    for turn in history[-_HISTORY_TURNS:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append(
        {
            "role": "user",
            "content": f"Source excerpts:\n\n{context}\n\nQuestion: {query}",
        }
    )
    return msgs


async def _complete(
    db: AsyncSession,
    *,
    provider: str,
    model: str,
    credential_alias: str | None,
    system_prompt: str,
    messages: list[dict[str, str]],
    user_id: uuid.UUID | None,
    session_id: uuid.UUID | None = None,
) -> tuple[str, int]:
    cred = await resolve_credential(db, provider=provider, alias=credential_alias)

    async with run_logged(
        task_name="subject_qa.answer",
        provider=provider,
        model=model,
        credential_alias=credential_alias,
        user_id=user_id,
        meta={"stage": "qa"},
    ) as tel:
        if provider == "anthropic":
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=cred.api_key)
            if session_id is not None:
                # Streaming path — emit each delta to SSE as it arrives.
                pieces: list[str] = []
                input_tokens = 0
                output_tokens = 0
                async with client.messages.stream(
                    model=model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=messages,  # type: ignore[arg-type]
                ) as stream:
                    async for text in stream.text_stream:
                        if text:
                            pieces.append(text)
                            await safe_publish_chat(
                                session_id, {"type": "token", "delta": text}
                            )
                    final = await stream.get_final_message()
                    if final.usage:
                        input_tokens = final.usage.input_tokens
                        output_tokens = final.usage.output_tokens
                tel.record_tokens(input_tokens, output_tokens)
                return "".join(pieces), input_tokens + output_tokens

            resp = await client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
            )
            out = resp.content[0].text if resp.content else ""
            tel.record_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
            return out, resp.usage.input_tokens + resp.usage.output_tokens

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=cred.api_key)
        if session_id is not None:
            pieces: list[str] = []
            stream = await client.chat.completions.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "system", "content": system_prompt}, *messages],  # type: ignore[arg-type]
                stream=True,
                stream_options={"include_usage": True},
            )
            input_tokens = 0
            output_tokens = 0
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        pieces.append(delta)
                        await safe_publish_chat(
                            session_id, {"type": "token", "delta": delta}
                        )
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens
            tel.record_tokens(input_tokens, output_tokens)
            return "".join(pieces), input_tokens + output_tokens

        resp = await client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system_prompt}, *messages],  # type: ignore[arg-type]
        )
        out = resp.choices[0].message.content or ""
        total = 0
        if resp.usage:
            tel.record_tokens(resp.usage.prompt_tokens, resp.usage.completion_tokens)
            total = resp.usage.prompt_tokens + resp.usage.completion_tokens
        return out, total


def _citations_from_hits(hits: list[HybridHit]) -> list[Citation]:
    return [
        Citation(
            chunk_id=h.chunk_id,
            upload_id=h.upload_id,
            section_title=h.section_title,
            text=(h.text or "")[:1000],
        )
        for h in hits
    ]


def _resolve_citations(answer: str, hits: list[HybridHit]) -> list[Citation]:
    """Map `[#chunk_id]` markers in the answer back to retrieved hits.

    Falls back to the top hits when the model emitted no parseable markers, so
    the UI always has something grounded to show.
    """
    by_id = {str(h.chunk_id): h for h in hits}
    cited: list[Citation] = []
    seen: set[str] = set()
    for raw in _CITATION_RE.findall(answer):
        hit = by_id.get(raw)
        if hit and raw not in seen:
            seen.add(raw)
            cited.append(
                Citation(
                    chunk_id=hit.chunk_id,
                    upload_id=hit.upload_id,
                    section_title=hit.section_title,
                    text=(hit.text or "")[:1000],
                )
            )
    if cited:
        return cited
    return _citations_from_hits(hits[:3])
