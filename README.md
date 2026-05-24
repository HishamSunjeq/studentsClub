# StudentsClub
11
An AI-powered study platform. Students upload lecture notes, past papers, and study materials; the platform generates grounded multiple-choice quizzes, supports per-subject Q&A chat, and exposes a full admin control plane for prompts, models, credentials, and retrieval settings.

> ## Work in progress
>
> This project is under **active development** and not yet production-ready. APIs, schemas, and the UI change frequently. Default credentials in `docker-compose.yml` and `backend/.env.example` are for **local development only** — generate fresh secrets before exposing this to anything beyond `localhost`. There are known rough edges; see [docs/roadmap.md](docs/roadmap.md) for current status.

---

## What's in the box

- **Multi-stage AI pipeline** — analyze → segment → retrieve (hybrid RAG) → generate → judge → dedupe → finalize, with SSE progress streaming.
- **Top-tier RAG on Qdrant** — dense (`text-embedding-3-small`) + sparse (BM25) hybrid search, contextual retrieval, optional reranker.
- **Layout-aware extraction** — runs `unstructured-api` as a Docker service; correctly handles Arabic / RTL text and scanned PDFs.
- **Admin control plane (UI)** — manage prompts, generation profiles, encrypted API credentials, the model registry, and extraction settings without touching env files.
- **Subject Q&A chat** — per-subject grounded chat with citations into uploaded material.

---

## Quick start

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/), [Node.js 20+](https://nodejs.org/) with [pnpm](https://pnpm.io/), and (optionally) [uv](https://docs.astral.sh/uv/) for running backend tools outside the container.

```bash
git clone <repo-url> studentsClub
cd studentsClub
cp backend/.env.example backend/.env       # defaults are fine for local Docker
docker compose up --build
```

In a second terminal, start the frontend:

```bash
cd frontend/apps/web
pnpm install
pnpm dev
```

| Service | URL |
|---|---|
| Web app | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| Qdrant dashboard | http://localhost:6333/dashboard |

A default admin (`admin@studentsclub.io` / `admin12345`) is seeded on first boot. **Change the password immediately.**

For anything beyond a local try-out — including how the pipeline works, how to configure providers from the UI, how to add models, how the RAG layer is wired, and how to run tests — see the docs.

---

## Documentation

| Doc | What it covers |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Services, data flow, queues, where state lives |
| [docs/ai-pipeline.md](docs/ai-pipeline.md) | Orchestrator stages, SSE events, replay |
| [docs/rag.md](docs/rag.md) | Qdrant collections, hybrid search, embeddings, reranker |
| [docs/extraction.md](docs/extraction.md) | `unstructured-api`, OCR languages, RTL/Arabic handling |
| [docs/admin.md](docs/admin.md) | Prompts, profiles, credentials, model registry, extraction settings |
| [docs/development.md](docs/development.md) | Local dev workflow, tests, migrations, codegen |
| [docs/environment.md](docs/environment.md) | Full env var reference |
| [docs/roadmap.md](docs/roadmap.md) | Phase status |

Per-part READMEs:

- [backend/README.md](backend/README.md) — FastAPI app, Celery workers, AI subsystem
- [frontend/README.md](frontend/README.md) — React + Vite app, Orval-generated API client
- [api's/README.md](api's/README.md) — Postman collections (manual API exploration)

---

## License

TBD. Until a license is added, **all rights reserved** — treat this code as source-available for review only.
