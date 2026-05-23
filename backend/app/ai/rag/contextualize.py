"""Contextual retrieval — Anthropic-style chunk pre-summarization (Phase 3).

For each chunk we ask a cheap LLM to write ONE short sentence describing
the chunk's topic, prepended to the chunk text before embedding. This
significantly boosts hybrid recall on dense-only similarity. Results are
cached by `hash(doc_title + section_title + chunk_text)` so the same
chunk is never summarized twice across uploads.
"""

from __future__ import annotations

import asyncio
import logging

from app.ai import cache as ai_cache

logger = logging.getLogger(__name__)


async def contextualize_chunks(
    chunks: list[dict],
    *,
    provider_name: str = "anthropic",
    credential_alias: str | None = None,
    model: str | None = None,
    concurrency: int = 4,
) -> list[str | None]:
    """Return a list of 1-sentence summaries (or None on failure) aligned
    with `chunks`. Each chunk dict must have keys: text, section_title,
    doc_title.
    """
    sem = asyncio.Semaphore(concurrency)

    async def one(chunk: dict) -> str | None:
        key = ai_cache.hash_key(
            "contextualize",
            chunk.get("doc_title", ""),
            chunk.get("section_title") or "",
            chunk.get("text", "")[:4000],
        )
        cached = await ai_cache.get("contextualize", key)
        if cached and isinstance(cached, dict) and "summary" in cached:
            return cached["summary"]

        async with sem:
            try:
                summary = await _summarize_one(
                    chunk=chunk,
                    provider_name=provider_name,
                    credential_alias=credential_alias,
                    model=model,
                )
            except Exception:
                logger.exception("contextualize failed for chunk; using None")
                summary = None

        if summary:
            await ai_cache.set("contextualize", key, {"summary": summary})
        return summary

    return await asyncio.gather(*[one(c) for c in chunks])


async def _summarize_one(
    *,
    chunk: dict,
    provider_name: str,
    credential_alias: str | None,
    model: str | None,
) -> str | None:
    from app.ai.credentials import resolve as resolve_credential
    from app.ai.prompts_registry import get_active_prompt
    from app.core.database import AsyncSessionLocal

    prompt = (await get_active_prompt("contextualize.chunk")).content

    async with AsyncSessionLocal() as db:
        cred = await resolve_credential(db, provider=provider_name, alias=credential_alias)

    user = (
        f"Document title: {chunk.get('doc_title') or '(untitled)'}\n"
        f"Section title: {chunk.get('section_title') or '(none)'}\n"
        f"Chunk:\n{chunk.get('text', '')[:4000]}"
    )

    if provider_name == "anthropic":
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=cred.api_key)
        resp = await client.messages.create(
            model=model or "claude-haiku-4-5",
            max_tokens=120,
            system=prompt,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip() if resp.content else None

    if provider_name == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=cred.api_key)
        resp = await client.chat.completions.create(
            model=model or "gpt-4o-mini",
            max_tokens=120,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip() or None

    return None
