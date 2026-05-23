"""Async Qdrant client + collection bootstrap (Phase 3).

A single shared `AsyncQdrantClient` instance per process. On first use,
it asserts both `chunks` and `questions` collections exist and creates
them with the right schema if not (hybrid: dense+sparse, scalar
quantization on the dense vector, payload indexes on `subject_id`).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# Imported lazily so unit tests / environments without qdrant-client installed
# still import this module without exploding.
_client = None
_bootstrap_lock = asyncio.Lock()
_bootstrapped = False

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@dataclass
class CollectionsConfig:
    chunks: str
    questions: str
    dense_dim: int


def _config() -> CollectionsConfig:
    from app.ai.rag import CHUNKS_COLLECTION, QUESTIONS_COLLECTION

    return CollectionsConfig(
        chunks=CHUNKS_COLLECTION,
        questions=QUESTIONS_COLLECTION,
        dense_dim=1536,  # text-embedding-3-small. Override via re-embed if you change models.
    )


async def get_client():
    """Return a process-singleton AsyncQdrantClient. Bootstraps collections on first call."""
    global _client, _bootstrapped
    if _client is None:
        from qdrant_client import AsyncQdrantClient

        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            prefer_grpc=settings.qdrant_prefer_grpc,
        )
    if not _bootstrapped:
        async with _bootstrap_lock:
            if not _bootstrapped:
                await _ensure_collections(_client)
                _bootstrapped = True
    return _client


async def close_client() -> None:
    global _client, _bootstrapped
    if _client is not None:
        try:
            await _client.close()
        except Exception:
            pass
    _client = None
    _bootstrapped = False


async def _ensure_collections(client) -> None:
    from qdrant_client import models

    cfg = _config()

    # chunks: dense + sparse, dense scalar-quantized.
    if not await _has_collection(client, cfg.chunks):
        await client.create_collection(
            collection_name=cfg.chunks,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=cfg.dense_dim,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                ),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False),
                )
            },
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    always_ram=True,
                )
            ),
        )
        await _create_payload_indexes(client, cfg.chunks, ["subject_id", "upload_id", "language", "doc_type"])
        logger.info("Created Qdrant collection %s", cfg.chunks)

    # questions: dense only.
    if not await _has_collection(client, cfg.questions):
        await client.create_collection(
            collection_name=cfg.questions,
            vectors_config=models.VectorParams(
                size=cfg.dense_dim,
                distance=models.Distance.COSINE,
                on_disk=True,
            ),
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    always_ram=True,
                )
            ),
        )
        await _create_payload_indexes(client, cfg.questions, ["subject_id", "published"])
        logger.info("Created Qdrant collection %s", cfg.questions)


async def _has_collection(client, name: str) -> bool:
    try:
        cols = await client.get_collections()
        return any(c.name == name for c in cols.collections)
    except Exception:
        return False


async def _create_payload_indexes(client, collection: str, fields: list[str]) -> None:
    from qdrant_client import models

    for field in fields:
        try:
            await client.create_payload_index(
                collection_name=collection,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:
            # Index may already exist — ignore.
            logger.debug("payload index create %s.%s skipped: %s", collection, field, exc)
