from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.users import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse, operation_id="users_get_me")
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
