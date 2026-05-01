import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.subjects import EnrollmentResponse, SubjectListResponse, SubjectResponse
from app.services import subjects_service

router = APIRouter()


@router.get("", response_model=SubjectListResponse)
async def list_subjects(
    db: DBSession,
    college: str | None = Query(default=None),
    academic_year: int | None = Query(default=None, ge=1, le=7),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SubjectListResponse:
    result = await subjects_service.list_subjects(
        db=db, college=college, academic_year=academic_year, page=page, size=size
    )
    return SubjectListResponse(
        items=[SubjectResponse.model_validate(s) for s in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/me", response_model=SubjectListResponse)
async def my_subjects(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SubjectListResponse:
    result = await subjects_service.my_subjects(
        db=db, user=current_user, page=page, size=size
    )
    return SubjectListResponse(
        items=[SubjectResponse.model_validate(s) for s in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: uuid.UUID, db: DBSession) -> SubjectResponse:
    subject = await subjects_service.get_subject(db=db, subject_id=subject_id)
    return SubjectResponse.model_validate(subject)


@router.post("/{subject_id}/enroll", response_model=EnrollmentResponse, status_code=201)
async def enroll(
    subject_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> EnrollmentResponse:
    enrollment = await subjects_service.enroll(
        db=db, user=current_user, subject_id=subject_id
    )
    return EnrollmentResponse.model_validate(enrollment)


@router.delete("/{subject_id}/enroll", status_code=204)
async def unenroll(
    subject_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> None:
    await subjects_service.unenroll(db=db, user=current_user, subject_id=subject_id)
