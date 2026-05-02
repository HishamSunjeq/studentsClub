# StudentsClub

An AI-powered study platform where students upload lecture notes, past papers, and study materials, and the platform automatically generates multiple-choice quiz questions using large language models. Students browse subjects, enrol, upload documents, and practise with generated quizzes.

---

## Features

- **Auth** — Register, login, JWT access + refresh tokens, logout
- **Subjects & Enrolment** — Browse a subject catalogue organised by college; enrol and unenrol
- **File Uploads** — Upload PDFs, Word documents, and images directly to S3-compatible storage via presigned PUT URLs
- **AI Extraction** — Background pipeline parses uploaded files and calls Anthropic or OpenAI to generate structured multiple-choice questions
- **Question Review** — *(Phase 5, in progress)* Approve, reject, and publish AI-generated question sets
- **Quiz Player** — *(Phase 6, upcoming)* Timed quiz sessions with attempt recording and scoring

---

## Tech Stack

### Backend
| Layer | Choice |
|---|---|
| Runtime | Python 3.12 |
| Web framework | FastAPI 0.118 (async) |
| ORM | SQLAlchemy 2.0 (asyncpg) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Auth | PyJWT + Passlib/bcrypt |
| Background jobs | Celery 5 + Redis |
| Object storage | MinIO (S3-compatible) via boto3 |
| File parsing | pdfplumber, python-docx, pytesseract/Pillow |
| AI providers | Anthropic SDK (prompt caching), OpenAI SDK (JSON mode) |
| Logging | structlog |
| Package manager | uv |

### Frontend
| Layer | Choice |
|---|---|
| Framework | React 19 + TypeScript |
| Build tool | Vite |
| Styling | Tailwind CSS 4 + shadcn/ui (Radix UI) |
| Routing | React Router 7 |
| Server state | TanStack Query 5 |
| Client state | Zustand |
| Forms | React Hook Form + Zod |
| HTTP client | Axios (JWT interceptor + refresh) |
| API codegen | Orval (reads FastAPI OpenAPI spec) |
| Notifications | Sonner |

### Infrastructure
| Service | Image |
|---|---|
| PostgreSQL | postgres:16-alpine |
| Redis | redis:7-alpine |
| MinIO | minio/minio:latest |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [uv](https://docs.astral.sh/uv/) — for running backend tooling outside Docker (tests, migrations, linting)
- [Node.js 20+](https://nodejs.org/) + [pnpm](https://pnpm.io/) — for frontend development

---

## Getting Started

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd studentsClub
```

Copy and edit the backend environment file:

```bash
cp backend/.env.example backend/.env
```

The defaults work for local Docker development. To enable real AI extraction, set either:

```
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...
AI_PROVIDER=anthropic   # or openai
```

### 2. Start all services

```bash
docker compose up --build
```

This starts: PostgreSQL, Redis, MinIO, the FastAPI API server, a Celery worker, and a Celery beat scheduler.

### 3. Run database migrations

In a separate terminal (once the API container is healthy):

```bash
docker compose exec api uv run alembic upgrade head
```

### 4. Seed subjects *(optional)*

```bash
docker compose exec api uv run python scripts/seed_subjects.py
```

This inserts 24 subjects across 3 colleges.

### 5. Start the frontend

```bash
cd frontend/apps/web
pnpm install
pnpm dev
```

The app is available at **http://localhost:5173**.

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API docs (ReDoc) | http://localhost:8000/redoc |
| MinIO console | http://localhost:9001 |

MinIO console credentials: `minio` / `minio12345`

---

## Project Structure

```
studentsClub/
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── .env.example
│   ├── docker/
│   │   └── Dockerfile          # Multi-stage dev/prod build
│   ├── scripts/
│   │   ├── start_api.sh
│   │   ├── start_worker.sh
│   │   ├── start_beat.sh
│   │   └── seed_subjects.py
│   ├── app/
│   │   ├── ai/                 # Providers (Anthropic, OpenAI), parsers, prompts
│   │   ├── api/v1/             # FastAPI routers: auth, subjects, uploads
│   │   ├── core/               # Config, database, security, logging
│   │   ├── db/migrations/      # Alembic env + versioned migrations
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic (auth, subjects, uploads, storage)
│   │   └── workers/tasks/      # Celery tasks: process_upload, extract_questions
│   └── tests/
│       ├── conftest.py         # Async test client, per-test DB rollback
│       ├── test_auth.py
│       ├── test_subjects.py
│       ├── test_uploads.py
│       └── test_parsers.py
└── frontend/apps/web/
    ├── orval.config.ts         # API client codegen config
    └── src/
        ├── api/                # Axios client + JWT interceptor
        ├── features/
        │   ├── auth/           # Login, Register pages
        │   ├── subjects/       # Subject browse + enrol
        │   └── uploads/        # Upload flow (drag-and-drop + S3 direct PUT)
        ├── components/         # Shared UI components
        └── hooks/              # Custom React hooks
```

---

## Development

### Backend — run tests

```bash
cd backend
uv run pytest -v
```

Tests use an in-memory SQLite-compatible async setup with per-test transaction rollback. S3 calls and Celery task dispatch are monkeypatched.

### Backend — linting and type checking

```bash
uv run ruff check .
uv run mypy app
```

### Backend — create a new migration

```bash
uv run alembic revision -m "describe_change"
# Edit the generated file, then apply:
uv run alembic upgrade head
```

### Frontend — generate API client from OpenAPI spec

Run this after the backend is serving on port 8000:

```bash
cd frontend/apps/web
pnpm api:gen
```

### Frontend — type check

```bash
pnpm tsc --noEmit
```

### Frontend — lint

```bash
pnpm lint
```

---

## Upload Flow

```
Browser → POST /api/v1/uploads          (creates Upload row, returns presigned PUT URL)
       → PUT  <presigned S3 URL>         (browser uploads file directly to MinIO)
       → POST /api/v1/uploads/{id}/finalize

Celery worker:
  process_upload task → downloads file from S3 → parses text → chunks
  extract_questions task → calls AI provider → stores QuestionSet + Questions + Choices
```

---

## Environment Variables

See `backend/.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis URL for caching |
| `CELERY_BROKER_URL` | Redis URL for Celery broker |
| `S3_ENDPOINT_URL` | MinIO/S3 endpoint (internal Docker URL) |
| `S3_PUBLIC_ENDPOINT_URL` | Presigned URL rewrite for browser access |
| `AI_PROVIDER` | `mock`, `anthropic`, or `openai` |
| `ANTHROPIC_API_KEY` | Required when `AI_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Required when `AI_PROVIDER=openai` |
| `SECRET_KEY` | JWT signing secret (min 32 chars) |

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0–1 | Auth, core infrastructure | ✅ Done |
| 2 | Subjects + enrolment | ✅ Done |
| 3 | File uploads + storage | ✅ Done |
| 4 | AI extraction pipeline | ✅ Done |
| 5 | Question review + publish | 🟡 In progress |
| 6 | Quiz sessions + scoring | ⬜ Upcoming |
| 7 | Flags + community votes | ⬜ Upcoming |
| 8 | Profile, stats, deployment | ⬜ Upcoming |
