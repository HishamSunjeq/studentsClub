from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.question import QuestionChoice
from app.schemas.question_sets import (
    QuestionChoiceResponse,
    QuestionResponse,
    QuestionUpdateRequest,
)
from app.services import question_sets_service

router = APIRouter()


@router.patch("/{question_id}", response_model=QuestionResponse, operation_id="questions_update")
async def update_question(
    question_id: UUID,
    payload: QuestionUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> QuestionResponse:
    question = await question_sets_service.update_question(
        db=db, question_id=question_id, user=current_user, payload=payload
    )
    choices = list(
        await db.scalars(
            select(QuestionChoice)
            .where(QuestionChoice.question_id == question.id)
            .order_by(QuestionChoice.position)
        )
    )
    return QuestionResponse(
        id=question.id,
        question_set_id=question.question_set_id,
        text=question.text,
        explanation=question.explanation,
        difficulty=question.difficulty,
        source_excerpt=question.source_excerpt,
        is_active=question.is_active,
        position=question.position,
        choices=[QuestionChoiceResponse.model_validate(c) for c in choices],
    )


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="questions_deactivate")
async def deactivate_question(
    question_id: UUID, current_user: CurrentUser, db: DBSession
) -> None:
    await question_sets_service.deactivate_question(
        db=db, question_id=question_id, user=current_user
    )
