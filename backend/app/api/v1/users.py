from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.users import (
    ContinueSessionResponse,
    RecommendedSubjectItem,
    UserProfileResponse,
    UserResponse,
    UserStatsResponse,
)
from app.services import profile_service, stats_service

router = APIRouter()


@router.get("/me", response_model=UserResponse, operation_id="users_get_me")
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/me/stats",
    response_model=UserStatsResponse,
    operation_id="users_get_me_stats",
)
async def get_my_stats(
    current_user: CurrentUser, db: DBSession
) -> UserStatsResponse:
    payload = await stats_service.get_user_stats(db=db, user=current_user)
    return UserStatsResponse(**payload)


@router.get(
    "/me/continue",
    response_model=ContinueSessionResponse | None,
    operation_id="users_get_me_continue",
)
async def get_my_continue(
    current_user: CurrentUser, db: DBSession
) -> ContinueSessionResponse | None:
    pair = await stats_service.get_continue_session(db=db, user=current_user)
    if pair is None:
        return None
    session, subject = pair
    answered = await stats_service.get_continue_session_progress(
        db=db, session_id=session.id
    )
    total = session.total_questions or 1
    return ContinueSessionResponse(
        session_id=session.id,
        subject_id=subject.id,
        subject_name=subject.name,
        subject_code=subject.code,
        total_questions=session.total_questions,
        answered_questions=answered,
        progress=round(answered / total, 4) if total else 0.0,
        started_at=session.created_at,
    )


@router.get(
    "/me/recommended-subjects",
    response_model=list[RecommendedSubjectItem],
    operation_id="users_get_me_recommended_subjects",
)
async def get_my_recommended_subjects(
    current_user: CurrentUser, db: DBSession
) -> list[RecommendedSubjectItem]:
    subjects = await stats_service.get_recommended_subjects(
        db=db, user=current_user, limit=4
    )
    return [RecommendedSubjectItem.model_validate(s) for s in subjects]


@router.get(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    operation_id="users_get_profile",
)
async def get_user_profile(
    user_id: UUID,
    db: DBSession,
    _current: CurrentUser,  # require auth, but profile is otherwise public-shaped
) -> UserProfileResponse:
    payload = await profile_service.get_user_profile(db=db, user_id=user_id)
    return UserProfileResponse(**payload)
