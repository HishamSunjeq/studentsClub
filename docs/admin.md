# Admin control plane

Everything an operator should tune at runtime is DB-backed and editable from the web UI. No env-file restarts required for prompts, models, credentials, profiles, or extraction settings.

Admin routes live under `/admin/*` in the web app and `/api/v1/admin/*` in the backend. Access requires `users.is_admin = true`. The first admin is seeded on first boot (`DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` in `docker-compose.yml`). **Change the password before doing anything else.**

## Pages

### Prompts (`/admin/prompts`)

Versioned prompt registry (`ai_prompts` table). One active version per `name` enforced by a partial unique index.

- **List** — grouped by `name`; shows all versions with `is_active` flag and content (Monaco editor).
- **Create new version** — drafts an inactive version. Save, review, then activate.
- **Activate / rollback** — flips the active flag; takes effect on the next request (60s TTL cache in `app/ai/prompts.py`).
- **Diff** — version vs version, or vs the currently active.
- **Test panel** — paste sample text, pick a model + credential, run a one-shot completion against the prompt.

Seeded prompts: `extraction.system`, `judge.rubric`, `contextualize.chunk`, `subject_qa.system`, `hyde.expand`.

### Profiles (`/admin/profiles`)

Per-subject and global generation profiles (`generation_profiles`). Each profile pins:

- Models — extraction, judge, embedding, rerank (FKs into `ai_models`, filtered by `kind`).
- Credentials — separate alias per stage (extraction / judge / embedding / rerank).
- Behaviour — `target_count`, `difficulty_mix` (3 sliders summing to 1), `judge_threshold`, `dedup_threshold`, `top_k_retrieval`, `top_n_rerank`, `hybrid_alpha`.

Resolution falls back: subject profile → global default profile (`is_default=true`) → registry defaults (top active model per kind from `ai_models`). See [ai-pipeline.md](ai-pipeline.md#profiles-and-overrides).

### Credentials (`/admin/credentials`)

Encrypted provider keys (`ai_credentials`). Backed by Fernet symmetric encryption with the master key from `AI_CREDENTIAL_KEY`.

- **Storage** — `key_encrypted bytea` only. Plaintext is encrypted on insert and decrypted only at provider-call time inside `app/ai/credentials.py::resolve(...)`. **The browser never receives a full key.**
- **Display** — every API response includes `key_last4` only (e.g. `sk-…ab12`).
- **Actions** — Add, Rotate (replace key, keep alias), Edit (display name + monthly budget), Revoke, Test (dry-runs a 1-token completion).
- **Cost rollup** — month-to-date USD computed from `ai_runs` joined on `credential_alias`.

Resolution priority for a provider call:

1. Explicit `credential_alias` arg.
2. Profile's stage-specific alias (`credential_alias_extraction`, etc.).
3. Subject default.
4. Global default for the provider.
5. `.env` fallback (back-compat — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, ...).

> **Public-repo note.** `AI_CREDENTIAL_KEY` in `docker-compose.yml` is a development default. **Generate a fresh Fernet key before deploying anywhere reachable.** Rotating this key invalidates every stored credential — re-enter them through the UI after rotation.

### Models (`/admin/models`)

Model registry (`ai_models`). Every provider call reads pricing, context window, and capability flags from here — nothing is hardcoded.

Columns: `provider`, `model_id` (e.g. `claude-opus-4-7`), `display_name`, `kind` (extraction / judge / embedding / rerank / chat / vision), `context_window`, `max_output_tokens`, `input_cost_per_mtoken`, `output_cost_per_mtoken`, `supports_streaming`, `supports_json_mode`, `supports_prompt_cache`, `embedding_dim`, `is_active`, `sort_order`.

**"Used by" column** combines two pieces of information:

- **profile-ref count** — number of `generation_profiles` rows referencing this model across any of the four FK slots.
- **`default` badge** — model is the **top active row** for its `kind` ordered by `sort_order`. This is what the registry resolver returns when no profile pins a model — i.e. what actually runs in the absence of overrides.

Reorder by changing `sort_order`. Deactivating a model removes it from the dropdowns in Profiles and from the registry-default resolver.

### Extraction (`/admin/extraction`)

Single global row controlling the document extractor. See [extraction.md](extraction.md#admin-settings) for the full field reference.

### Runs (`/admin/runs`)

Paginated table over `ai_runs`. Filters: question_set, provider, credential alias, model, status, time range. Per-row detail drawer with full payload, parent run, and retry chain. Top-of-page rollup: total cost MTD, by provider, by model, by credential alias.

### Dashboard (`/admin/dashboard`)

Aggregate charts: tokens/day, cost/day, p50/p95 latency, cache hit rate. Powered by `GET /admin/ai/metrics?range=30`. The endpoint sums booleans via `CASE WHEN` (not `CAST(bool AS numeric)`) — asyncpg refuses the implicit cast.

## Replay

`POST /api/v1/question-sets/{id}/replay` with optional `prompt_version_id`, `model_id`, `profile_id`, `credential_alias`. Clones the set (linked via `parent_question_set_id`) and dispatches the canvas. The Review page renders side-by-side diff against the parent.

## Security notes for going public

- The `AI_CREDENTIAL_KEY` default in `docker-compose.yml` is **not secret** — it's a known value in this repo. Generate a fresh key before any non-local deployment:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

- `SECRET_KEY` (JWT signing) and `DEFAULT_ADMIN_PASSWORD` defaults are likewise dev-only.
- Plaintext API keys never appear in DB dumps, logs, or HTTP responses. Verified by `SELECT encode(key_encrypted, 'hex') FROM ai_credentials` returning ciphertext bytea.
- SSE endpoints take the JWT as a `?token=` query parameter (EventSource limitation). The token is short-lived but does land in server access logs; rotate to cookie-based session auth if logs are sensitive.
