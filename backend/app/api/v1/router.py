from fastapi import APIRouter

from app.api.v1 import auth, question_sets, questions, quizzes, subjects, uploads, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(question_sets.router, prefix="/question-sets", tags=["question-sets"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["quizzes"])
