# @studentsclub/web

The web application. React 19 + TypeScript + Vite.

This README is intentionally brief — see the parent [frontend/README.md](../../README.md) for layout, codegen, and dev workflow, and the repo-root [docs/](../../../docs/) for architecture, AI pipeline, RAG, and admin documentation.

## Common commands

```bash
pnpm install
pnpm dev              # http://localhost:5173
pnpm api:gen          # regenerate src/api/generated/ from the backend's OpenAPI spec
pnpm tsc --noEmit
pnpm lint
pnpm build
```

The Vite dev server expects the backend on `http://localhost:8000`. Start the full stack with `docker compose up` from the repo root.
