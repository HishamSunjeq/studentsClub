from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.users import UserResponse
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201, operation_id="auth_register")
async def register(body: RegisterRequest, db: DBSession) -> TokenResponse:
    _, tokens = await auth_service.register(
        db=db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        college=body.college,
        academic_year=body.academic_year,
    )
    return tokens


@router.post("/login", response_model=TokenResponse, operation_id="auth_login")
async def login(body: LoginRequest, db: DBSession) -> TokenResponse:
    _, tokens = await auth_service.login(db=db, email=body.email, password=body.password)
    return tokens


@router.post("/refresh", response_model=TokenResponse, operation_id="auth_refresh")
async def refresh(body: RefreshRequest, db: DBSession) -> TokenResponse:
    return await auth_service.refresh(db=db, raw_token=body.refresh_token)


@router.post("/logout", status_code=204, operation_id="auth_logout")
async def logout(body: LogoutRequest, db: DBSession) -> None:
    await auth_service.logout(db=db, raw_token=body.refresh_token)


@router.post("/change-password", status_code=204, operation_id="auth_change_password")
async def change_password(
    body: ChangePasswordRequest, current_user: CurrentUser, db: DBSession
) -> None:
    await auth_service.change_password(
        db=db,
        user=current_user,
        current_password=body.current_password,
        new_password=body.new_password,
    )


@router.post("/forgot-password", status_code=204, operation_id="auth_forgot_password")
async def forgot_password(body: ForgotPasswordRequest, db: DBSession) -> None:
    await auth_service.forgot_password(db=db, email=body.email)


@router.post("/reset-password", status_code=204, operation_id="auth_reset_password")
async def reset_password(body: ResetPasswordRequest, db: DBSession) -> None:
    await auth_service.reset_password(
        db=db, raw_token=body.token, new_password=body.new_password
    )
