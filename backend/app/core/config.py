from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-key-change-this-in-production-32chars"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    database_url: str = "postgresql+asyncpg://studentsclub:dev@localhost:5432/studentsclub"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    s3_endpoint_url: str | None = None
    s3_public_endpoint_url: str | None = None  # browser-reachable URL (differs in Docker)
    s3_bucket: str = "studentsclub-uploads"
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    ai_provider: str = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # AI rate limits (Phase 1). Per-provider request and token rates per minute.
    # Defaults are generous; tighten in production based on actual quotas.
    ai_default_rpm: int = 60
    ai_default_tpm: int = 100_000
    anthropic_rpm: int = 50
    anthropic_tpm: int = 80_000
    openai_rpm: int = 500
    openai_tpm: int = 200_000
    openai_embed_rpm: int = 3000

    # Qdrant (Phase 3 RAG)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_prefer_grpc: bool = False

    # Document extraction (Phase 9). `extraction_backend` is the fallback used
    # when no `extraction_settings` row exists; the DB row takes precedence.
    unstructured_api_url: str = "http://localhost:8001"
    extraction_backend: str = "unstructured"  # or "legacy"

    # AI cost guardrails (Phase 1).
    user_daily_token_budget: int = 500_000
    qs_max_tokens: int = 200_000

    # AI result cache TTL (Phase 1).
    ai_cache_ttl_seconds: int = 60 * 60 * 24  # 24h

    # AI credential encryption master key (Phase 2). Fernet 32-byte url-safe base64.
    # Empty in dev — credentials feature gracefully degrades to env-only when missing.
    ai_credential_key: str = ""

    # Default admin seeded on first boot if no admin exists. Override the password
    # in any non-local deployment.
    default_admin_email: str = "admin@studentsclub.io"
    default_admin_password: str = "admin12345"
    default_admin_name: str = "Default Admin"
    default_admin_college: str = "Administration"
    default_admin_year: int = 1
    default_admin_seed_enabled: bool = True

    max_upload_bytes: int = 52_428_800
    daily_upload_limit_per_user: int = 10

    cors_origins: list[str] = ["http://localhost:5173"]
    frontend_url: str = "http://localhost:5173"
    password_reset_token_ttl_minutes: int = 60  # 1 hour

    # Optional SMTP — if not set, reset links are logged to console instead
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@studentsclub.local"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v  # type: ignore[return-value]


settings = Settings()
