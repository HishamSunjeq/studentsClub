# Frontend

React 19 + TypeScript + Vite. Tailwind CSS 4, shadcn/ui (Radix), React Router 7, TanStack Query 5, Zustand, React Hook Form + Zod, Sonner for toasts, and **Orval** for type-safe API hooks generated from the backend's OpenAPI spec.

For the high-level system view, see [../docs/architecture.md](../docs/architecture.md). For local dev workflow (codegen, type-check, lint), see [../docs/development.md](../docs/development.md).

---

## Layout

The repo is a pnpm workspace; the only app today is `apps/web`.

```
frontend/
├── package.json                  # workspace root
├── pnpm-lock.yaml
└── apps/web/
    ├── orval.config.ts           # codegen — reads http://localhost:8000/openapi.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    └── src/
        ├── main.tsx
        ├── app/
        │   ├── router.tsx        # Route tree, lazy admin routes
        │   ├── shell/            # AppShell, Sidebar, header
        │   └── providers/        # QueryClient, ThemeProvider
        ├── api/
        │   ├── axios.ts          # JWT interceptor + token refresh
        │   └── generated/        # Orval output (do not edit by hand)
        ├── features/
        │   ├── auth/             # Login, Register
        │   ├── subjects/         # Catalogue, detail, chat panel
        │   ├── uploads/          # Drag-drop, SSE progress, generation panel
        │   ├── question-sets/    # Review, publish, replay diff
        │   └── admin/            # Prompts, Profiles, Credentials, Models, Extraction, Runs, Dashboard
        ├── components/
        │   ├── ui/               # shadcn primitives
        │   └── design/           # EmptyState, etc.
        └── hooks/
```

---

## Running

```bash
cd frontend/apps/web
pnpm install
pnpm dev          # http://localhost:5173
```

The dev server proxies `http://localhost:8000` for API calls. Start the backend (`docker compose up`) first.

---

## Codegen

After any backend endpoint or schema change:

```bash
cd frontend/apps/web
pnpm api:gen      # runs orval against the live backend
```

This refreshes `src/api/generated/`. Never edit generated files by hand. The generated TanStack Query hooks (`useAdminModelsList`, `useUploadsGenerationDefaults`, etc.) are the only sanctioned way to call the backend.

---

## Type-check and lint

```bash
pnpm tsc --noEmit
pnpm lint
```

---

## Admin pages

`/admin/*` routes are lazy-loaded and gated on `is_admin`. The current set:

- `prompts` — versioned prompt registry with diff and activate
- `profiles` — per-subject generation profiles (model + credential + thresholds)
- `credentials` — encrypted provider keys (Fernet); plaintext never leaves the browser, never displayed
- `models` — model registry (provider, kind, pricing, sort_order, "used by")
- `extraction` — global extraction settings (backend, OCR languages, strategy)
- `runs` — `ai_runs` telemetry table with filters and detail drawer
- `dashboard` — token / cost / latency / cache-hit charts

See [../docs/admin.md](../docs/admin.md) for what each page controls and how it flows back to the orchestrator.

---

## More

- AI pipeline internals — [../docs/ai-pipeline.md](../docs/ai-pipeline.md)
- RAG / Qdrant — [../docs/rag.md](../docs/rag.md)
- Architecture overview — [../docs/architecture.md](../docs/architecture.md)
