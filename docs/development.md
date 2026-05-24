# Development workflow

Day-to-day commands for working on the backend and the web app.

## Prerequisites

| Tool | Why |
|---|---|
| Docker Desktop | Runs Postgres, Redis, MinIO, Qdrant, unstructured-api, and (optionally) the API + worker. |
| Node.js 20+ and pnpm | Web app. |
| uv | Python dep + venv manager for the backend. Optional if you run everything via docker compose. |

## Booting the stack

```bash
cp backend/.env.example backend/.env       # defaults work for local Docker
docker compose up --build
```

That runs every service. The API container runs migrations on boot via `start_api.sh`. A default admin is seeded on first boot.

Frontend separately:

```bash
cd frontend/apps/web
pnpm install
pnpm dev
```

## Running backend tools outside Docker

Faster iteration loop: bring up infra in Docker, run the API and worker on the host.

```bash
docker compose up -d postgres redis qdrant minio unstructured-api
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
# in another shell:
uv run celery -A app.workers.celery_app worker -Q uploads,ai,embeddings,celery -l info
```

When running on the host, `backend/.env` must point at `localhost` for Postgres / Redis / Qdrant / MinIO rather than the docker-compose service names.

## Tests

```bash
cd backend
uv run pytest -v
uv run pytest tests/test_orchestrator.py -v       # one file
uv run pytest -k "credentials and rotate"          # filter
```

Tests use an async Postgres test database with per-test transaction rollback. `AI_PROVIDER=mock` returns canned analyze/generate output so no API keys are needed.

The Postman collections under [`api's/`](../api's/README.md) cover the manual-exploration use case.

## Lint, types

```bash
# Backend
cd backend
uv run ruff check .
uv run mypy app

# Frontend
cd frontend/apps/web
pnpm tsc --noEmit
pnpm lint
```

## Migrations

```bash
cd backend
uv run alembic revision -m "describe_change"   # autogenerate edit
# review the generated file under app/db/migrations/versions/, then:
uv run alembic upgrade head
```

A few conventions:

- `server_default` for `uuid[]` columns must be `sa.text("'{}'::uuid[]")`. `"ARRAY[]::uuid[]"` looks correct but asyncpg cannot prepare it.
- Enum types are created at the migration level and reused by SQLAlchemy `Enum(name=...)`. Don't define enums inline.
- When changing embedding-relevant columns, bump `embedding_version` on `document_chunks` and queue `scripts/reembed.py`.

## API client codegen

The web app's typed hooks live in `frontend/apps/web/src/api/generated/`. They're regenerated from the live backend's OpenAPI spec.

```bash
cd frontend/apps/web
pnpm api:gen
```

This calls Orval, which reads `http://localhost:8000/openapi.json`. The backend must be running.

Conventions:

- Every endpoint must have an explicit `operation_id` — Orval uses it to name the generated hook. Add `operation_id="uploads_generation_defaults"` etc. on the FastAPI route.
- Never edit generated files by hand.
- After a backend schema or route change, regenerate, then `pnpm tsc --noEmit`.

## Seeding

```bash
docker compose exec api uv run python scripts/seed_subjects.py
```

Inserts 24 subjects across 3 colleges. The model registry, prompt registry, and a default generation profile are seeded by migrations on first boot.

## Logs

- API: `docker compose logs -f api`
- Worker: `docker compose logs -f worker`
- SSE traffic: open the browser dev tools Network tab, filter by `events`.

## Common gotchas

- **Asyncpg DDL casts.** `CAST(bool AS numeric)` is rejected; use `CASE WHEN bool THEN 1 ELSE 0 END`. Several admin metrics queries already do this.
- **Celery + asyncio.** Each task creates its own event loop. `WORKER_MODE=1` switches DB sessions to `NullPool` so connections aren't reused across loops.
- **MinIO presigned URLs.** Browser uploads go through `S3_PUBLIC_ENDPOINT_URL` (`http://localhost:9000`), worker downloads via `S3_ENDPOINT_URL` (`http://minio:9000`). Both must be set.
- **EventSource auth.** SSE routes take JWT as `?token=`, not the `Authorization` header — browsers can't set headers on `EventSource`.
- **Qdrant boot race.** The compose file doesn't healthcheck Qdrant; the client retries on first call. If you hit a connection error on the very first generation after a cold start, retry.
