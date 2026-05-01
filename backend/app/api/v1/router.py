from fastapi import APIRouter

from app.api.v1 import auth, subjects, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])

# Future routers — uncomment as each phase ships:
# from app.api.v1 import uploads, question_sets, questions, quizzes
# api_router.include_router(uploads.router,       prefix="/uploads",       tags=["uploads"])
# api_router.include_router(question_sets.router, prefix="/question-sets", tags=["question-sets"])
# api_router.include_router(questions.router,     prefix="/questions",     tags=["questions"])
# api_router.include_router(quizzes.router,       prefix="/quizzes",       tags=["quizzes"])
