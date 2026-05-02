from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.core.logging import configure_logging
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    import structlog
    from app.services import storage_service
    log = structlog.get_logger()
    try:
        storage_service.ensure_bucket_exists()
    except Exception as exc:
        log.warning("storage_setup_failed", error=str(exc))
    yield


app = FastAPI(
    title="StudentsClub API",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready() -> dict[str, str]:
    # Phase 1: add DB + Redis + S3 checks here
    return {"status": "ok"}
