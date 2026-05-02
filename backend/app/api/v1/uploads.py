from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.uploads import PresignResponse, UploadCreateRequest, UploadResponse
from app.services import uploads_service

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PresignResponse)
async def create_upload(
    payload: UploadCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> PresignResponse:
    return await uploads_service.create_upload(db=db, user=current_user, payload=payload)


@router.post("/{upload_id}/finalize", response_model=UploadResponse)
async def finalize_upload(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> UploadResponse:
    upload = await uploads_service.finalize_upload(
        db=db, upload_id=upload_id, user=current_user
    )
    return UploadResponse.model_validate(upload)


@router.get("/{upload_id}", response_model=UploadResponse)
async def get_upload(
    upload_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> UploadResponse:
    upload = await uploads_service.get_upload(
        db=db, upload_id=upload_id, user=current_user
    )
    return UploadResponse.model_validate(upload)
