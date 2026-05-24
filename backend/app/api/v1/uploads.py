from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.models.upload import UploadStatus
from app.schemas.uploads import (
    GenerateRequest,
    GenerateResponse,
    GenerationDefaultsResponse,
    PresignResponse,
    PreviewUrlResponse,
    UploadCreateRequest,
    UploadDetailResponse,
    UploadListResponse,
    UploadResponse,
    UploadUpdateRequest,
)
from app.services import uploads_service

router = APIRouter()


@router.get("", response_model=UploadListResponse, operation_id="uploads_list")
async def list_uploads(
    current_user: CurrentUser,
    db: DBSession,
    status_filter: UploadStatus | None = Query(default=None, alias="status"),
    subject_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> UploadListResponse:
    return await uploads_service.list_uploads(
        db=db,
        user=current_user,
        status_filter=status_filter,
        subject_id=subject_id,
        page=page,
        size=size,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PresignResponse,
    operation_id="uploads_create",
)
async def create_upload(
    payload: UploadCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> PresignResponse:
    return await uploads_service.create_upload(
        db=db, user=current_user, payload=payload
    )


@router.post(
    "/{upload_id}/finalize",
    response_model=UploadResponse,
    operation_id="uploads_finalize",
)
async def finalize_upload(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> UploadResponse:
    upload = await uploads_service.finalize_upload(
        db=db, upload_id=upload_id, user=current_user
    )
    return UploadResponse.model_validate(upload)


@router.get(
    "/{upload_id}", response_model=UploadDetailResponse, operation_id="uploads_get"
)
async def get_upload(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> UploadDetailResponse:
    return await uploads_service.get_upload_detail(
        db=db, upload_id=upload_id, user=current_user
    )


@router.patch(
    "/{upload_id}", response_model=UploadResponse, operation_id="uploads_update"
)
async def update_upload(
    upload_id: UUID,
    payload: UploadUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> UploadResponse:
    upload = await uploads_service.update_upload(
        db=db, upload_id=upload_id, user=current_user, payload=payload
    )
    return UploadResponse.model_validate(upload)


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="uploads_delete",
)
async def delete_upload(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await uploads_service.delete_upload(
        db=db, upload_id=upload_id, user=current_user
    )


@router.get(
    "/{upload_id}/preview-url",
    response_model=PreviewUrlResponse,
    operation_id="uploads_preview_url",
)
async def get_preview_url(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> PreviewUrlResponse:
    return await uploads_service.get_preview_url(
        db=db, upload_id=upload_id, user=current_user
    )


@router.get(
    "/{upload_id}/generation-defaults",
    response_model=GenerationDefaultsResponse,
    operation_id="uploads_generation_defaults",
)
async def generation_defaults(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> GenerationDefaultsResponse:
    return await uploads_service.get_generation_defaults(
        db=db, upload_id=upload_id, user=current_user
    )


@router.post(
    "/{upload_id}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerateResponse,
    operation_id="uploads_generate",
)
async def generate_questions(
    upload_id: UUID,
    payload: GenerateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> GenerateResponse:
    return await uploads_service.generate_questions(
        db=db, upload_id=upload_id, user=current_user, payload=payload
    )
