"""Embed an upload's extracted text into Qdrant + `document_chunks` (Phase 3).

Pipeline:
  1. Load upload + extracted text
  2. Split via heading-aware recursive splitter
  3. Contextualize each chunk (cheap LLM, cached) — prepend a 1-sentence
     summary to the chunk text before embedding
  4. Dense embed via OpenAI `text-embedding-3-small`
  5. Sparse encode via local BM25 (fastembed)
  6. Bulk-insert into Postgres `document_chunks` (chunk metadata + text +
     contextual summary) — these UUIDs ARE the Qdrant point IDs
  7. Upsert multi-vector points into Qdrant `chunks` collection

Chained from `process_upload.run` after extraction succeeds. Runs on the
`embeddings` queue so it doesn't compete with synchronous AI generation.

Idempotent: deletes existing chunks for the upload (Qdrant + Postgres)
before re-inserting, so a retried task converges to the same state.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.embed_chunks.run",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run(self, upload_id: str) -> dict:  # type: ignore[return]
    try:
        return asyncio.run(_async_run(upload_id))
    except Exception as exc:
        logger.exception("embed_chunks failed for upload=%s", upload_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _async_run(upload_id: str) -> dict:
    from sqlalchemy import delete, select

    from app.ai.rag import EMBEDDING_VERSION
    from app.ai.rag.contextualize import contextualize_chunks
    from app.ai.rag.embedder.factory import get_embedder
    from app.ai.rag.embedder.sparse import BM25SparseEncoder
    from app.ai.rag.index import ChunkUpsert, delete_by_upload, upsert_chunks
    from app.ai.rag.splitter import split_document
    from app.core.database import AsyncSessionLocal
    from app.models.document_chunk import DocumentChunk
    from app.models.upload import Upload

    upload_uuid = uuid.UUID(upload_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Upload).where(Upload.id == upload_uuid))
        upload = result.scalar_one_or_none()
        if upload is None:
            raise ValueError(f"Upload {upload_id} not found")
        if not upload.extracted_text or not upload.extracted_text.strip():
            logger.info("Upload %s has no extracted text; skipping embed", upload_id)
            return {"upload_id": upload_id, "chunks": 0, "skipped": True}

        text = upload.extracted_text
        subject_id = upload.subject_id
        doc_title = upload.original_filename or "(untitled)"

    split = split_document(text)
    if not split:
        logger.info("No chunks produced for upload=%s", upload_id)
        return {"upload_id": upload_id, "chunks": 0}

    # 1. Contextualize (parallel, cached). Per-chunk summaries to boost recall.
    chunk_dicts = [
        {
            "text": sc.text,
            "section_title": sc.section_title,
            "doc_title": doc_title,
        }
        for sc in split
    ]
    try:
        summaries = await contextualize_chunks(chunk_dicts)
    except Exception:
        logger.exception("Contextualize step failed; embedding without summaries")
        summaries = [None] * len(split)

    # 2. Build the "text to embed" — prepend summary if available.
    embed_texts = []
    for sc, summary in zip(split, summaries):
        prefix = f"{summary.strip()}\n\n" if summary else ""
        embed_texts.append(f"{prefix}{sc.text}")

    # 3. Dense embed (OpenAI) + sparse encode (local BM25), in parallel.
    embedder = await get_embedder()
    sparse_encoder = BM25SparseEncoder()

    dense_task = asyncio.create_task(embedder.embed(embed_texts))
    sparse_task = asyncio.create_task(sparse_encoder.encode(embed_texts))
    dense_vectors, sparse_vectors = await asyncio.gather(dense_task, sparse_task)

    if len(dense_vectors) != len(split) or len(sparse_vectors) != len(split):
        raise RuntimeError(
            f"Embedding count mismatch: split={len(split)} dense={len(dense_vectors)} "
            f"sparse={len(sparse_vectors)}"
        )

    # 4. Wipe-and-replace for idempotency (retries + re-embeds).
    await delete_by_upload(upload_uuid)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.upload_id == upload_uuid)
            )

    # 5. Bulk-insert Postgres rows first (source of truth) — IDs propagate to Qdrant.
    chunk_rows: list[DocumentChunk] = []
    chunk_upserts: list[ChunkUpsert] = []
    for sc, summary, dense, sparse in zip(split, summaries, dense_vectors, sparse_vectors):
        chunk_id = uuid.uuid4()
        chunk_rows.append(
            DocumentChunk(
                id=chunk_id,
                upload_id=upload_uuid,
                subject_id=subject_id,
                position=sc.position,
                section_title=sc.section_title,
                text=sc.text,
                contextual_summary=summary,
                token_count=len(sc.text) // 4,  # rough token estimate
                language=None,
                doc_type=None,
                embedding_model=embedder.name,
                embedding_version=EMBEDDING_VERSION,
                meta={},
            )
        )
        chunk_upserts.append(
            ChunkUpsert(
                chunk_id=chunk_id,
                upload_id=upload_uuid,
                subject_id=subject_id,
                section_title=sc.section_title,
                position=sc.position,
                language=None,
                doc_type=None,
                text=sc.text,
                dense=dense,
                sparse=sparse,
                embedding_model=embedder.name,
            )
        )

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add_all(chunk_rows)

    # 6. Upsert points into Qdrant.
    await upsert_chunks(chunk_upserts)

    logger.info("Embedded upload=%s into %d chunks", upload_id, len(chunk_upserts))
    return {
        "upload_id": upload_id,
        "chunks": len(chunk_upserts),
        "embedding_model": embedder.name,
        "embedding_version": EMBEDDING_VERSION,
    }
