# Roadmap

The project ships in phases. Each phase is self-contained enough to demo; the headline AI work (orchestrator + RAG + admin control plane) landed in phases 1–7, with phases 8 and 9 hardening and finishing the extraction story.

| Phase | Scope | Status |
|---|---|---|
| 0 | Bootstrap, infra, CI plumbing | Done |
| 1 | Auth, JWT refresh, base routers | Done |
| 2 | Subjects + enrolment | Done |
| 3 | File uploads + S3/MinIO | Done |
| 4 | First-pass AI extraction (single-call) | Done |
| 5 | Question Set review + publish | Done |
| 6 | Quiz sessions + attempts (UI scaffolding) | In progress |
| **AI overhaul P1** | Telemetry (`ai_runs`), rate limits, budgets, DLQ, Celery hardening | Done |
| **AI overhaul P2** | Prompt registry, generation profiles, encrypted credentials, model registry | Done |
| **AI overhaul P3** | Qdrant + RAG indexing (hybrid, contextual, scalar-quantized) | Done |
| **AI overhaul P4** | Multi-stage orchestrator (HyDE, rerank, judge, dedupe) | Done |
| **AI overhaul P5** | SSE streaming UX | Done |
| **AI overhaul P6** | Replay + full admin frontend (Prompts/Profiles/Credentials/Models/Runs/Dashboard) | Done |
| **AI overhaul P7** | Subject Q&A chat with citations | Done |
| **AI overhaul P8** | Hardening + end-to-end verification fixes | Done |
| **AI overhaul P9** | unstructured.io extraction + model-selection clarity | Done |
| 7 | Flags, community votes, moderation | Upcoming |
| 8 | Public profile, stats, deployment polish | Upcoming |

## Known rough edges (as of the latest commit)

- Subject chat currently polls in some code paths; the SSE consumer for chat is being switched in. See Phase 8 H1 notes in the planning history.
- Per-question regenerate from the Review page does not yet thread RAG context through the modal (Phase 8 H3).
- The retrieve stage handles Qdrant outages by surfacing `retrieve.degraded` on the SSE stream, but a richer "system status" surface in the admin dashboard is still pending.
- No CI in this repo yet — tests run locally.
- License is **TBD**. Until then, all rights are reserved.

## Out of scope for now

- Multi-tenant hosting / org accounts.
- Mobile clients.
- Self-hosted embedding / reranker models (the reranker and embedder Protocols make this a small addition when needed).
