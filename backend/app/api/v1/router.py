from fastapi import APIRouter

from app.api.v1 import (
    auth,
    chunks,
    feed,
    notifications,
    question_sets,
    questions,
    quizzes,
    search,
    subjects,
    uploads,
    uploads_events,
    users,
)
from app.api.v1.admin import (
    ai_metrics as admin_ai_metrics,
    ai_runs as admin_ai_runs,
    credentials as admin_credentials,
    models as admin_models,
    profiles as admin_profiles,
    prompts as admin_prompts,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(uploads_events.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(question_sets.router, prefix="/question-sets", tags=["question-sets"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(chunks.router, prefix="/chunks", tags=["chunks"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(feed.router, prefix="/feed", tags=["feed"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
api_router.include_router(
    notifications.settings_router, prefix="/users/me/settings", tags=["settings"]
)

# Admin control plane (Phase 2). All routes are gated by `require_admin`.
api_router.include_router(admin_prompts.router,      prefix="/admin/prompts",     tags=["admin"])
api_router.include_router(admin_credentials.router,  prefix="/admin/credentials", tags=["admin"])
api_router.include_router(admin_models.router,       prefix="/admin/models",      tags=["admin"])
api_router.include_router(admin_profiles.router,     prefix="/admin/profiles",    tags=["admin"])
api_router.include_router(admin_ai_runs.router,       prefix="/admin/ai/runs",     tags=["admin"])
api_router.include_router(admin_ai_metrics.router,    prefix="/admin/ai/metrics",  tags=["admin"])
