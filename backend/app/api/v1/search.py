from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.subjects import SearchResponse
from app.services import profile_service

router = APIRouter()


@router.get(
    "",
    response_model=SearchResponse,
    operation_id="search_query",
)
async def search(
    db: DBSession,
    _current: CurrentUser,
    q: str = Query(default="", description="Search query"),
    limit: int = Query(default=10, ge=1, le=25),
) -> SearchResponse:
    payload = await profile_service.search(db=db, q=q, limit=limit)
    return SearchResponse(**payload)
