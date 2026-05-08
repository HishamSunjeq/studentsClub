from fastapi import APIRouter

from app.api.v1 import (
    auth,
    feed,
    notifications,
    question_sets,
    questions,
    quizzes,
    search,
    subjects,
    uploads,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(question_sets.router, prefix="/question-sets", tags=["question-sets"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(feed.router, prefix="/feed", tags=["feed"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
api_router.include_router(
    notifications.settings_router, prefix="/users/me/settings", tags=["settings"]
)
