"""Qdrant index operations: upsert + hybrid search + delete (Phase 3).

The chunks collection holds multi-vector points (dense + sparse) keyed
by the same UUID as the Postgres `document_chunks.id` row. The
questions collection holds dense-only points keyed by `question_id`.

Hybrid search uses Qdrant's `Query API` with a `prefetch` of dense and
sparse candidates fused with RRF. The fusion weight isn't a separate
"alpha" — RRF is rank-based — but `alpha` is exposed for compatibility
with the generation profile (mapped to relative prefetch limits).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.ai.rag import CHUNKS_COLLECTION, EMBEDDING_VERSION, QUESTIONS_COLLECTION
from app.ai.rag.embedder.sparse import SparseVec
from app.ai.rag.qdrant_client import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME, get_client

logger = logging.getLogger(__name__)


@dataclass
class ChunkUpsert:
    chunk_id: uuid.UUID
    upload_id: uuid.UUID
    subject_id: uuid.UUID | None
    section_title: str | None
    position: int
    language: str | None
    doc_type: str | None
    text: str  # truncated to ~2KB on insert
    dense: list[float]
    sparse: SparseVec
    embedding_model: str


@dataclass
class HybridHit:
    chunk_id: uuid.UUID
    upload_id: uuid.UUID | None
    subject_id: uuid.UUID | None
    section_title: str | None
    text: str
    score: float


async def upsert_chunks(chunks: list[ChunkUpsert]) -> None:
    if not chunks:
        return
    from qdrant_client import models

    client = await get_client()
    points = [
        models.PointStruct(
            id=str(c.chunk_id),
            vector={
                DENSE_VECTOR_NAME: c.dense,
                SPARSE_VECTOR_NAME: models.SparseVector(
                    indices=c.sparse.indices, values=c.sparse.values
                ),
            },
            payload={
                "chunk_id": str(c.chunk_id),
                "upload_id": str(c.upload_id),
                "subject_id": str(c.subject_id) if c.subject_id else None,
                "section_title": c.section_title,
                "position": c.position,
                "language": c.language,
                "doc_type": c.doc_type,
                "text": c.text[:2000],
                "embedding_model": c.embedding_model,
                "embedding_version": EMBEDDING_VERSION,
            },
        )
        for c in chunks
    ]
    await client.upsert(collection_name=CHUNKS_COLLECTION, points=points, wait=False)


async def upsert_question(
    *,
    question_id: uuid.UUID,
    subject_id: uuid.UUID | None,
    dense: list[float],
    published: bool,
    embedding_model: str,
) -> None:
    from qdrant_client import models

    client = await get_client()
    point = models.PointStruct(
        id=str(question_id),
        vector=dense,
        payload={
            "question_id": str(question_id),
            "subject_id": str(subject_id) if subject_id else None,
            "published": published,
            "embedding_model": embedding_model,
            "embedding_version": EMBEDDING_VERSION,
        },
    )
    await client.upsert(collection_name=QUESTIONS_COLLECTION, points=[point], wait=False)


async def hybrid_search(
    *,
    subject_id: uuid.UUID | None,
    dense: list[float],
    sparse: SparseVec,
    k: int = 50,
    alpha: float = 0.5,
    upload_id: uuid.UUID | None = None,
    language: str | None = None,
) -> list[HybridHit]:
    """RRF-fused dense + sparse retrieval. `alpha` shifts relative
    prefetch sizes (alpha=1.0 = dense-only, alpha=0.0 = sparse-only).
    """
    from qdrant_client import models

    client = await get_client()

    must: list[models.FieldCondition] = []
    if subject_id is not None:
        must.append(
            models.FieldCondition(key="subject_id", match=models.MatchValue(value=str(subject_id)))
        )
    if upload_id is not None:
        must.append(
            models.FieldCondition(key="upload_id", match=models.MatchValue(value=str(upload_id)))
        )
    if language is not None:
        must.append(
            models.FieldCondition(key="language", match=models.MatchValue(value=language))
        )
    payload_filter = models.Filter(must=must) if must else None

    dense_limit = max(20, int(200 * alpha))
    sparse_limit = max(20, int(200 * (1.0 - alpha)))

    result = await client.query_points(
        collection_name=CHUNKS_COLLECTION,
        prefetch=[
            models.Prefetch(
                query=dense,
                using=DENSE_VECTOR_NAME,
                limit=dense_limit,
                filter=payload_filter,
            ),
            models.Prefetch(
                query=models.SparseVector(indices=sparse.indices, values=sparse.values),
                using=SPARSE_VECTOR_NAME,
                limit=sparse_limit,
                filter=payload_filter,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=k,
        with_payload=True,
    )

    return [
        HybridHit(
            chunk_id=uuid.UUID(str(p.id)),
            upload_id=_maybe_uuid(p.payload.get("upload_id")),
            subject_id=_maybe_uuid(p.payload.get("subject_id")),
            section_title=p.payload.get("section_title"),
            text=p.payload.get("text") or "",
            score=p.score,
        )
        for p in result.points
    ]


async def search_questions(
    *,
    subject_id: uuid.UUID | None,
    dense: list[float],
    threshold: float,
    only_published: bool = True,
    limit: int = 10,
) -> list[tuple[uuid.UUID, float]]:
    from qdrant_client import models

    client = await get_client()
    must: list[models.FieldCondition] = []
    if subject_id is not None:
        must.append(
            models.FieldCondition(key="subject_id", match=models.MatchValue(value=str(subject_id)))
        )
    if only_published:
        must.append(
            models.FieldCondition(key="published", match=models.MatchValue(value=True))
        )
    payload_filter = models.Filter(must=must) if must else None

    result = await client.query_points(
        collection_name=QUESTIONS_COLLECTION,
        query=dense,
        limit=limit,
        filter=payload_filter,
        score_threshold=threshold,
        with_payload=False,
    )
    return [(uuid.UUID(str(p.id)), p.score) for p in result.points]


async def delete_by_upload(upload_id: uuid.UUID) -> None:
    from qdrant_client import models

    client = await get_client()
    await client.delete(
        collection_name=CHUNKS_COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="upload_id", match=models.MatchValue(value=str(upload_id))
                    )
                ]
            )
        ),
        wait=False,
    )


async def delete_question(question_id: uuid.UUID) -> None:
    client = await get_client()
    await client.delete(
        collection_name=QUESTIONS_COLLECTION,
        points_selector=[str(question_id)],
        wait=False,
    )


def _maybe_uuid(v) -> uuid.UUID | None:
    if not v:
        return None
    try:
        return uuid.UUID(str(v))
    except Exception:
        return None
