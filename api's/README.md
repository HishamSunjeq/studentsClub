# Postman collections + API reference

This folder is the **manual-API surface** for StudentsClub. Each tag in the backend's OpenAPI spec gets two files:

- `<Tag>.postman_collection.json` — importable into Postman / Insomnia / Bruno / Hoppscotch.
- `<Tag>.md` — human-readable endpoint list with summaries, body schemas, and auth requirements.

The source of truth is always the live OpenAPI document at `http://localhost:8000/openapi.json` (or the Swagger UI at `/docs`). These files are generated from it by [`_generate.py`](_generate.py) and should be regenerated after any backend route change:

```bash
python "api's/_generate.py"
```

> The folder name `api's` is a historical typo and will be renamed in a future commit.

## Collections

| Tag | Postman | Reference |
|---|---|---|
| Auth | [Auth.postman_collection.json](Auth.postman_collection.json) | [Auth.md](Auth.md) |
| Users | [Users.postman_collection.json](Users.postman_collection.json) | [Users.md](Users.md) |
| Settings | [Settings.postman_collection.json](Settings.postman_collection.json) | [Settings.md](Settings.md) |
| Subjects | [Subjects.postman_collection.json](Subjects.postman_collection.json) | [Subjects.md](Subjects.md) |
| Subject Chat | [Subject_Chat.postman_collection.json](Subject_Chat.postman_collection.json) | [Subject_Chat.md](Subject_Chat.md) |
| Uploads | [Uploads.postman_collection.json](Uploads.postman_collection.json) | [Uploads.md](Uploads.md) |
| Question Sets | [Question_Sets.postman_collection.json](Question_Sets.postman_collection.json) | [Question_Sets.md](Question_Sets.md) |
| Questions | [Questions.postman_collection.json](Questions.postman_collection.json) | [Questions.md](Questions.md) |
| Quizzes | [Quizzes.postman_collection.json](Quizzes.postman_collection.json) | [Quizzes.md](Quizzes.md) |
| Feed | [Feed.postman_collection.json](Feed.postman_collection.json) | [Feed.md](Feed.md) |
| Notifications | [Notifications.postman_collection.json](Notifications.postman_collection.json) | [Notifications.md](Notifications.md) |
| Search | [Search.postman_collection.json](Search.postman_collection.json) | [Search.md](Search.md) |
| Chunks | [Chunks.postman_collection.json](Chunks.postman_collection.json) | [Chunks.md](Chunks.md) |
| Admin | [Admin.postman_collection.json](Admin.postman_collection.json) | [Admin.md](Admin.md) |
| Health | [Health.postman_collection.json](Health.postman_collection.json) | [Health.md](Health.md) |

## Environment

[`StudentsClub.postman_environment.json`](StudentsClub.postman_environment.json) wires every collection to your local backend.

- `base_url` → `http://localhost:8000/api/v1`
- `root_url` → `http://localhost:8000` (used by `/health`)
- `access_token` / `refresh_token` — populated automatically by the Auth → Login / Register / Refresh test scripts.
- ID variables (`subject_id`, `upload_id`, `question_set_id`, `session_id`, `prompt_id`, `credential_id`, `model_id`, `profile_id`, `run_id`, …) — set them manually as you click through requests, or via test scripts.

## Usage

1. Start the backend: `docker compose up` from the repo root.
2. In Postman, **Import** every `*.postman_collection.json` plus the environment file. Select the `StudentsClub - Local` environment.
3. Run `Auth → Login` (or `Register`) first — the test script saves the tokens into the environment.
4. Subsequent requests in every collection use `{{access_token}}` as the bearer.

## What each collection covers

- **Auth** — register, login, refresh, logout, change/forgot/reset password.
- **Users** — `me`, stats, continue, recommended subjects, public profile lookup.
- **Settings** — per-user app settings (theme, locale, etc).
- **Subjects** — catalogue (public), enrolment, members, published sets, leaderboard.
- **Subject Chat** — per-subject RAG chat. Sessions, messages, SSE events.
- **Uploads** — presigned PUT flow, finalize, generation kickoff, SSE progress stream.
- **Question Sets** — draft review, publish, reject, replay.
- **Questions** — per-question edit, deactivate, regenerate (RAG-grounded), retrieval preview.
- **Quizzes** — start, answer, complete, list, result.
- **Feed** — recent activity feed across enrolled subjects.
- **Notifications** — inbox, mark read.
- **Search** — cross-entity search.
- **Chunks** — document chunk lookup by ID (citation popovers).
- **Admin** — prompts, credentials, models, profiles, extraction settings, AI runs telemetry. Requires `is_admin=true`.
- **Health** — liveness + readiness.

## Regenerating after a backend change

```bash
# 1. Make sure the backend is running so openapi.json is fresh
cd frontend/apps/web && pnpm api:gen   # also refreshes the typed React Query hooks

# 2. Regenerate Postman + MD
python "api's/_generate.py"
```

The generator reads `frontend/apps/web/openapi.json`. If you've changed routes but not regenerated that file yet, the Postman collections will be stale.
