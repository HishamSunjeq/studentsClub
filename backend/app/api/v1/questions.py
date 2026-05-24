from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.question import QuestionChoice
from app.schemas.question_sets import (
    QuestionChoiceResponse,
    QuestionRegenerateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
    RetrievalPreviewChunk,
    RetrievalPreviewResponse,
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


@router.post(
    "/{question_id}/regenerate",
    response_model=QuestionResponse,
    operation_id="questions_regenerate",
)
async def regenerate_question(
    question_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    payload: QuestionRegenerateRequest | None = None,
) -> QuestionResponse:
    chunk_ids = payload.chunk_ids if payload else None
    question = await question_sets_service.regenerate_question(
        db=db, question_id=question_id, user=current_user, chunk_ids=chunk_ids
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


@router.get(
    "/{question_id}/retrieval-preview",
    response_model=RetrievalPreviewResponse,
    operation_id="questions_retrieval_preview",
)
async def retrieval_preview(
    question_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> RetrievalPreviewResponse:
    ctx = await question_sets_service.retrieval_preview_for_question(
        db=db, question_id=question_id, user=current_user
    )
    return RetrievalPreviewResponse(
        question_id=question_id,
        query=ctx.query,
        hyde=ctx.hyde,
        chunks=[
            RetrievalPreviewChunk(
                chunk_id=c.chunk_id,
                upload_id=c.upload_id,
                section_title=c.section_title,
                text=c.text,
                score=c.score,
            )
            for c in ctx.chunks
        ],
        degraded=ctx.degraded,
        degraded_reason=ctx.degraded_reason,
    )
