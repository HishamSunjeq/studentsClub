from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.models.quiz import QuizSessionStatus
from app.schemas.quizzes import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizChoiceResponse,
    QuizQuestionResponse,
    QuizResultResponse,
    QuizSessionListResponse,
    QuizSessionResponse,
    QuizSessionWithQuestionsResponse,
    QuizStartRequest,
)
from app.services import quizzes_service

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=QuizSessionWithQuestionsResponse, operation_id="quizzes_start")
async def start_quiz(
    payload: QuizStartRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> QuizSessionWithQuestionsResponse:
    session, questions, choices_by_q = await quizzes_service.start_quiz(
        db=db,
        user=current_user,
        subject_id=payload.subject_id,
        count=payload.count,
        difficulties=payload.difficulties,
    )
    return QuizSessionWithQuestionsResponse(
        id=session.id,
        user_id=session.user_id,
        subject_id=session.subject_id,
        status=session.status,
        total_questions=session.total_questions,
        score=session.score,
        completed_at=session.completed_at,
        created_at=session.created_at,
        questions=[
            QuizQuestionResponse(
                id=q.id,
                text=q.text,
                difficulty=q.difficulty,
                position=idx,
                choices=[
                    QuizChoiceResponse.model_validate(c)
                    for c in choices_by_q.get(q.id, [])
                ],
            )
            for idx, q in enumerate(questions)
        ],
    )


@router.get("/me", response_model=QuizSessionListResponse, operation_id="quizzes_list_mine")
async def list_my_quizzes(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status: QuizSessionStatus | None = Query(default=None),
    subject_id: UUID | None = Query(default=None),
) -> QuizSessionListResponse:
    result = await quizzes_service.list_my_sessions(
        db=db,
        user=current_user,
        page=page,
        size=size,
        status=status,
        subject_id=subject_id,
    )
    return QuizSessionListResponse(
        items=[QuizSessionResponse.model_validate(s) for s in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{session_id}", response_model=QuizSessionResponse, operation_id="quizzes_get")
async def get_quiz(
    session_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuizSessionResponse:
    session = await quizzes_service.get_session(
        db=db, session_id=session_id, user=current_user
    )
    return QuizSessionResponse.model_validate(session)


@router.get("/{session_id}/questions", response_model=QuizSessionWithQuestionsResponse, operation_id="quizzes_get_with_questions")
async def get_quiz_with_questions(
    session_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuizSessionWithQuestionsResponse:
    session, questions, choices_by_q, answered_ids = (
        await quizzes_service.get_session_with_questions(
            db=db, session_id=session_id, user=current_user
        )
    )
    return QuizSessionWithQuestionsResponse(
        id=session.id,
        user_id=session.user_id,
        subject_id=session.subject_id,
        status=session.status,
        total_questions=session.total_questions,
        score=session.score,
        completed_at=session.completed_at,
        created_at=session.created_at,
        questions=[
            QuizQuestionResponse(
                id=q.id,
                text=q.text,
                difficulty=q.difficulty,
                position=idx,
                choices=[
                    QuizChoiceResponse.model_validate(c)
                    for c in choices_by_q.get(q.id, [])
                ],
            )
            for idx, q in enumerate(questions)
        ],
        answered_question_ids=list(answered_ids),
    )


@router.post("/{session_id}/answer", response_model=QuizAnswerResponse, operation_id="quizzes_submit_answer")
async def submit_answer(
    session_id: UUID,
    payload: QuizAnswerRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> QuizAnswerResponse:
    _, correct_id, explanation, answered, score = await quizzes_service.submit_answer(
        db=db,
        session_id=session_id,
        user=current_user,
        question_id=payload.question_id,
        choice_id=payload.choice_id,
    )
    return QuizAnswerResponse(
        is_correct=(payload.choice_id == correct_id),
        correct_choice_id=correct_id,
        explanation=explanation,
        answered_count=answered,
        score=score,
    )


@router.get(
    "/{session_id}/result",
    response_model=QuizResultResponse,
    operation_id="quizzes_get_result",
)
async def get_quiz_result(
    session_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuizResultResponse:
    payload = await quizzes_service.get_quiz_result(
        db=db, session_id=session_id, user=current_user
    )
    return QuizResultResponse(**payload)


@router.post("/{session_id}/complete", response_model=QuizSessionResponse, operation_id="quizzes_complete")
async def complete_quiz(
    session_id: UUID, current_user: CurrentUser, db: DBSession
) -> QuizSessionResponse:
    session = await quizzes_service.complete_quiz(
        db=db, session_id=session_id, user=current_user
    )
    return QuizSessionResponse.model_validate(session)
