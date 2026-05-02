from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.models.question import QuestionSetStatus
from app.schemas.question_sets import (
    QuestionChoiceResponse,
    QuestionResponse,
    QuestionSetListResponse,
    QuestionSetResponse,
    QuestionSetUpdateRequest,
    QuestionSetWithQuestionsResponse,
)
from app.services import question_sets_service

router = APIRouter()


@router.get("/me", response_model=QuestionSetListResponse)
async def list_my_question_sets(
    current_user: CurrentUser,
    db: DBSession,
    status: QuestionSetStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> QuestionSetListResponse:
    result = await question_sets_service.list_my_drafts(
        db=db, user=current_user, status=status, page=page, size=size
    )
    return QuestionSetListResponse(
        items=[QuestionSetResponse.model_validate(qs) for qs in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{qs_id}", response_model=QuestionSetWithQuestionsResponse)
async def get_question_set(
    qs_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuestionSetWithQuestionsResponse:
    qs = await question_sets_service.get_with_questions(
        db=db, qs_id=qs_id, user=current_user
    )
    return QuestionSetWithQuestionsResponse(
        id=qs.id,
        upload_id=qs.upload_id,
        subject_id=qs.subject_id,
        created_by=qs.created_by,
        title=qs.title,
        status=qs.status,
        ai_model=qs.ai_model,
        tokens_used=qs.tokens_used,
        created_at=qs.created_at,
        updated_at=qs.updated_at,
        questions=[
            QuestionResponse(
                id=q.id,
                question_set_id=q.question_set_id,
                text=q.text,
                explanation=q.explanation,
                difficulty=q.difficulty,
                source_excerpt=q.source_excerpt,
                is_active=q.is_active,
                position=q.position,
                choices=[
                    QuestionChoiceResponse.model_validate(c)
                    for c in q.choices  # type: ignore[attr-defined]
                ],
            )
            for q in qs.questions  # type: ignore[attr-defined]
        ],
    )


@router.patch("/{qs_id}", response_model=QuestionSetResponse)
async def update_question_set(
    qs_id: UUID,
    payload: QuestionSetUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> QuestionSetResponse:
    qs = await question_sets_service.update_title(
        db=db, qs_id=qs_id, user=current_user, title=payload.title
    )
    return QuestionSetResponse.model_validate(qs)


@router.post("/{qs_id}/publish", response_model=QuestionSetResponse)
async def publish_question_set(
    qs_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuestionSetResponse:
    qs = await question_sets_service.publish(db=db, qs_id=qs_id, user=current_user)
    return QuestionSetResponse.model_validate(qs)


@router.post("/{qs_id}/reject", response_model=QuestionSetResponse)
async def reject_question_set(
    qs_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuestionSetResponse:
    qs = await question_sets_service.reject(db=db, qs_id=qs_id, user=current_user)
    return QuestionSetResponse.model_validate(qs)
