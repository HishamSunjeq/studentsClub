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
    s3_bucket: str = "studentsclub-uploads"
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    ai_provider: str = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    max_upload_bytes: int = 52_428_800
    daily_upload_limit_per_user: int = 10

    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v  # type: ignore[return-value]


settings = Settings()
