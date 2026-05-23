"""Stage 6: drop near-duplicates of already-published questions (Phase 4).

Embeds each accepted candidate and queries Qdrant `questions` collection
scoped to the subject. Any candidate scoring above `dedup_threshold`
(cosine) is dropped.
"""

from __future__ import annotations

import logging
import uuid

from app.ai.orchestrator.profile import ResolvedProfile
from app.ai.orchestrator.schemas import JudgedQuestion
from app.ai.rag.embedder.factory import get_embedder
from app.ai.rag.index import search_questions

logger = logging.getLogger(__name__)


async def dedupe_questions(
    *,
    profile: ResolvedProfile,
    judged: list[JudgedQuestion],
    subject_id: uuid.UUID | None,
) -> tuple[list[JudgedQuestion], int]:
    """Returns (kept, dropped_count). Auto-rejected questions are passed
    through unchanged so they can be persisted with `auto_rejected=true`.
    """
    if not judged:
        return [], 0

    # Only run dedup against the bank if we have a subject; otherwise skip.
    if subject_id is None:
        return judged, 0

    accepted = [j for j in judged if not j.auto_rejected]
    if not accepted:
        return judged, 0

    try:
        embedder = await get_embedder(
            credential_alias=profile.embedding_credential_alias,
            model=profile.embedding_model,
        )
        texts = [j.question.text for j in accepted]
        vectors = await embedder.embed(texts)
    except Exception:
        logger.exception("dedupe: embedding failed; skipping dedup pass")
        return judged, 0

    dropped = 0
    kept_by_idx: set[int] = set()
    for i, vec in enumerate(vectors):
        try:
            hits = await search_questions(
                subject_id=subject_id,
                dense=vec,
                threshold=profile.dedup_threshold,
                only_published=True,
                limit=1,
            )
        except Exception:
            logger.exception("dedupe: search_questions failed for candidate %d", i)
            hits = []
        if hits:
            dropped += 1
        else:
            kept_by_idx.add(i)

    # Reassemble final list preserving original order.
    final: list[JudgedQuestion] = []
    accept_idx = 0
    for j in judged:
        if j.auto_rejected:
            final.append(j)
            continue
        if accept_idx in kept_by_idx:
            final.append(j)
        accept_idx += 1

    return final, dropped
