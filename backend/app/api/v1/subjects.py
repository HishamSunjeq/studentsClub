import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.subjects import (
    EnrollmentResponse,
    SubjectContributorResponse,
    SubjectListResponse,
    SubjectMemberListResponse,
    SubjectPublishedSetListResponse,
    SubjectResponse,
)
from app.services import subjects_service

router = APIRouter()


def _build_subject_response(
    subject,
    member_counts: dict,
    qs_counts: dict,
    q_counts: dict,
) -> SubjectResponse:
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        code=subject.code,
        college=subject.college,
        academic_year=subject.academic_year,
        description=subject.description,
        created_at=subject.created_at,
        member_count=member_counts.get(subject.id, 0),
        published_question_set_count=qs_counts.get(subject.id, 0),
        question_count=q_counts.get(subject.id, 0),
    )


@router.get("", response_model=SubjectListResponse, operation_id="subjects_list")
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
    subject_ids = [s.id for s in result.items]
    member_counts, qs_counts, q_counts = await subjects_service.compute_aggregates(
        db, subject_ids
    )
    return SubjectListResponse(
        items=[_build_subject_response(s, member_counts, qs_counts, q_counts) for s in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/me", response_model=SubjectListResponse, operation_id="subjects_list_mine")
async def my_subjects(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SubjectListResponse:
    result = await subjects_service.my_subjects(
        db=db, user=current_user, page=page, size=size
    )
    subject_ids = [s.id for s in result.items]
    member_counts, qs_counts, q_counts = await subjects_service.compute_aggregates(
        db, subject_ids
    )
    return SubjectListResponse(
        items=[_build_subject_response(s, member_counts, qs_counts, q_counts) for s in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{subject_id}", response_model=SubjectResponse, operation_id="subjects_get")
async def get_subject(subject_id: uuid.UUID, db: DBSession) -> SubjectResponse:
    subject = await subjects_service.get_subject(db=db, subject_id=subject_id)
    member_counts, qs_counts, q_counts = await subjects_service.compute_aggregates(
        db, [subject.id]
    )
    return _build_subject_response(subject, member_counts, qs_counts, q_counts)


@router.post("/{subject_id}/enroll", response_model=EnrollmentResponse, status_code=201, operation_id="subjects_enroll")
async def enroll(
    subject_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> EnrollmentResponse:
    enrollment = await subjects_service.enroll(
        db=db, user=current_user, subject_id=subject_id
    )
    return EnrollmentResponse.model_validate(enrollment)


@router.delete("/{subject_id}/enroll", status_code=204, operation_id="subjects_unenroll")
async def unenroll(
    subject_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> None:
    await subjects_service.unenroll(db=db, user=current_user, subject_id=subject_id)


@router.get(
    "/{subject_id}/members",
    response_model=SubjectMemberListResponse,
    operation_id="subjects_get_members",
)
async def get_members(
    subject_id: uuid.UUID,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SubjectMemberListResponse:
    members, total = await subjects_service.get_members(
        db=db, subject_id=subject_id, page=page, size=size
    )
    pages = (total + size - 1) // size if total else 1
    return SubjectMemberListResponse(
        items=members, total=total, page=page, size=size, pages=pages
    )


@router.get(
    "/{subject_id}/top-contributors",
    response_model=list[SubjectContributorResponse],
    operation_id="subjects_get_top_contributors",
)
async def get_top_contributors(
    subject_id: uuid.UUID,
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[SubjectContributorResponse]:
    return await subjects_service.get_top_contributors(
        db=db, subject_id=subject_id, limit=limit
    )


@router.get(
    "/{subject_id}/question-sets",
    response_model=SubjectPublishedSetListResponse,
    operation_id="subjects_get_published_sets",
)
async def get_published_sets(
    subject_id: uuid.UUID,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SubjectPublishedSetListResponse:
    sets, total = await subjects_service.get_published_sets(
        db=db, subject_id=subject_id, page=page, size=size
    )
    pages = (total + size - 1) // size if total else 1
    return SubjectPublishedSetListResponse(
        items=sets, total=total, page=page, size=size, pages=pages
    )
