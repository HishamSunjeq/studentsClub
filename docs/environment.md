# Environment variables

The backend reads its config from environment variables (validated by `app/core/config.py`). `backend/.env.example` is the canonical list; this page explains the non-obvious ones and what to change before going to production.

> **Public-repo warning.** Several variables in `docker-compose.yml` ship with **development defaults that are not secret**: `SECRET_KEY`, `AI_CREDENTIAL_KEY`, `DEFAULT_ADMIN_PASSWORD`, `S3_SECRET_KEY`, and the Postgres password. They're fine for `localhost` only. Generate fresh values before exposing the stack to anything else.

## Core

| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | `development` | `development` / `staging` / `production`. Production tightens CORS and log formatting. |
| `SECRET_KEY` | dev string | JWT signing secret. Must be ≥32 chars in production. |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | JSON-encoded list. |

## Database

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://studentsclub:dev@postgres:5432/studentsclub` | Async DSN. |
| `RUN_MIGRATIONS` | `1` | API container runs `alembic upgrade head` on boot. The worker sets `0`. |
| `WORKER_MODE` | `0` | Workers set `1` so DB sessions use `NullPool` (Celery's per-task event loop). |

## Redis / Celery

| Variable | Default | Notes |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | App cache + rate limiter + SSE pub/sub. |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Task queue. |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Task results. |

## Object storage (MinIO / S3)

| Variable | Default | Notes |
|---|---|---|
| `S3_ENDPOINT_URL` | `http://minio:9000` | Internal docker-network URL the API/worker use. |
| `S3_PUBLIC_ENDPOINT_URL` | `http://localhost:9000` | Used to rewrite presigned URLs so the **browser** can hit MinIO directly. |
| `S3_BUCKET` | `studentsclub-uploads` | Created on boot if missing. |
| `S3_REGION` | `us-east-1` | |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `minio` / `minio12345` | MinIO root creds in dev. |

## Vector DB

| Variable | Default | Notes |
|---|---|---|
| `QDRANT_URL` | `http://qdrant:6333` | |
| `QDRANT_API_KEY` | (unset) | Required for Qdrant Cloud. |
| `QDRANT_PREFER_GRPC` | `true` | gRPC is faster for batch upserts. |

## Document extraction

| Variable | Default | Notes |
|---|---|---|
| `UNSTRUCTURED_API_URL` | `http://unstructured-api:8000` | Internal docker URL. Falls back to legacy parser if unreachable. |
| `EXTRACTION_BACKEND` | `unstructured` | `unstructured` or `legacy`. Overridden at runtime by the `extraction_settings` row. |

## AI providers (env fallback)

These are the **fallback** path used only when no matching `ai_credentials` row exists. Real usage stores credentials encrypted in the database via the admin Credentials page.

| Variable | Notes |
|---|---|
| `AI_PROVIDER` | `mock` / `anthropic` / `openai`. `mock` is the docker-compose default — switch to a real provider once a credential is added. |
| `ANTHROPIC_API_KEY` | Used when `AI_PROVIDER=anthropic` and no DB credential matches. |
| `OPENAI_API_KEY` | Same, for OpenAI. |
| `COHERE_API_KEY` | Reranker. |
| `VOYAGE_API_KEY` | Alternative reranker. |

## Credential encryption

| Variable | Default | Notes |
|---|---|---|
| `AI_CREDENTIAL_KEY` | dev key in compose | Fernet master key (url-safe 32-byte base64). **Rotate before deployment.** Rotating invalidates every stored credential — re-enter them through the UI after rotation. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

## Rate limits and budgets

| Variable | Default | Notes |
|---|---|---|
| `ANTHROPIC_TPM` | model-dependent | Token bucket per `(provider, credential_alias)`. |
| `OPENAI_RPM` | model-dependent | |
| `OPENAI_EMBED_RPM` | provider-dependent | Embedder calls use a separate bucket. |
| `USER_DAILY_TOKEN_BUDGET` | configurable | Per-user daily cap. 429 when exceeded. |
| `QS_MAX_TOKENS` | configurable | Per-question-set hard cap. |

Per-credential monthly USD caps are stored on `ai_credentials.monthly_budget_usd`, edited from the admin Credentials page.

## Default admin (first-boot seed)

| Variable | Default | Notes |
|---|---|---|
| `DEFAULT_ADMIN_EMAIL` | `admin@studentsclub.io` | |
| `DEFAULT_ADMIN_PASSWORD` | `admin12345` | **Change immediately after first login.** Only seeded when no admin row exists. |
| `DEFAULT_ADMIN_NAME` | `Default Admin` | |

## Going public — checklist

Before deploying anywhere reachable:

1. Generate a fresh `SECRET_KEY` (≥32 chars).
2. Generate a fresh `AI_CREDENTIAL_KEY` (Fernet).
3. Change `DEFAULT_ADMIN_PASSWORD` or pre-disable the seed by setting `DEFAULT_ADMIN_EMAIL=""`.
4. Set strong MinIO / Postgres credentials and **do not** commit them.
5. Tighten `CORS_ORIGINS` to your real frontend origin.
6. Switch `APP_ENV=production` so logs are JSON-formatted and CORS isn't permissive.
7. Put TLS in front of the API. SSE in particular relies on a long-lived HTTPS connection.
8. Audit `docker-compose.yml` — the dev compose file exposes Postgres, Redis, MinIO console, and Qdrant on host ports. Don't ship that to production as-is.
