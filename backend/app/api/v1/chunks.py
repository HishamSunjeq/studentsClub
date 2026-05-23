"""Source-chunk lookup for grounding/citation panels (Phase 6).

`GET /api/v1/chunks?ids=<uuid>,<uuid>` returns the chunk text behind a
question's `source_chunk_ids`. Access is ownership-scoped: a caller sees a
chunk only if they own the parent upload, unless they are an admin.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.document_chunk import DocumentChunk
from app.models.upload import Upload
from app.models.user import UserRole
from app.schemas.admin import ChunkListResponse, ChunkResponse

router = APIRouter()


@router.get("", response_model=ChunkListResponse, operation_id="chunks_by_ids")
async def get_chunks(
    current_user: CurrentUser,
    db: DBSession,
    ids: str = Query(..., description="Comma-separated chunk UUIDs"),
) -> ChunkListResponse:
    parsed: list[uuid.UUID] = []
    for raw in ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed.append(uuid.UUID(raw))
        except ValueError:
            continue
    if not parsed:
        return ChunkListResponse(items=[])

    q = select(DocumentChunk).where(DocumentChunk.id.in_(parsed))
    if current_user.role != UserRole.admin:
        # Restrict to chunks from the caller's own uploads.
        q = q.join(Upload, Upload.id == DocumentChunk.upload_id).where(
            Upload.user_id == current_user.id
        )
    rows = (await db.execute(q)).scalars().all()

    # Preserve the requested order so the UI lines citations up predictably.
    by_id = {r.id: r for r in rows}
    ordered = [by_id[i] for i in parsed if i in by_id]
    return ChunkListResponse(items=[ChunkResponse.model_validate(r) for r in ordered])
