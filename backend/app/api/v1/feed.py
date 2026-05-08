from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.users import FeedListResponse
from app.services import stats_service

router = APIRouter()


@router.get(
    "",
    response_model=FeedListResponse,
    operation_id="feed_list",
)
async def get_feed(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> FeedListResponse:
    payload = await stats_service.get_activity_feed(
        db=db, user=current_user, page=page, size=size
    )
    return FeedListResponse(**payload)
