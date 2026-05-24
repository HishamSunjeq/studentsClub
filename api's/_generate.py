"""Regenerate Postman collections + MD docs from the live OpenAPI spec.

Run from the repo root:
    python "api's/_generate.py"

Reads ../frontend/apps/web/openapi.json and writes one
<Tag>.postman_collection.json + <Tag>.md per tag into this folder.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).parent
SPEC = HERE.parent / "frontend" / "apps" / "web" / "openapi.json"

# Tag → output filename stem (Postman + MD use the same stem).
TAG_TO_NAME = {
    "auth": "Auth",
    "users": "Users",
    "subjects": "Subjects",
    "subject-chat": "Subject_Chat",
    "uploads": "Uploads",
    "question-sets": "Question_Sets",
    "questions": "Questions",
    "quizzes": "Quizzes",
    "feed": "Feed",
    "notifications": "Notifications",
    "search": "Search",
    "chunks": "Chunks",
    "admin": "Admin",
    "settings": "Settings",
    "health": "Health",
}

# Tag → human-friendly collection description.
TAG_DESCRIPTION = {
    "auth": "Authentication endpoints — register, login, refresh, logout, change/forgot/reset password.",
    "users": "Current-user profile, stats, continue-watching, recommended subjects, and public profile lookup.",
    "subjects": "Subject catalogue, enrolment, members, top contributors, published question sets, leaderboard.",
    "subject-chat": "Per-subject RAG-grounded Q&A chat. Sessions, message history, SSE event stream.",
    "uploads": "File uploads — presigned PUT flow, finalize, listing, generation kickoff, SSE stream.",
    "question-sets": "Draft review, publish/reject, replay against a different prompt/model/profile.",
    "questions": "Per-question edit, deactivate, regenerate with RAG context, retrieval preview.",
    "quizzes": "Quiz sessions: start, answer, complete, list, fetch result.",
    "feed": "Cross-subject feed of recent activity.",
    "notifications": "Notification inbox — list, mark read, mark all read.",
    "search": "Cross-entity search.",
    "chunks": "Look up document chunk excerpts by IDs (used by citation popovers).",
    "admin": "Admin control plane — prompts, credentials, models, profiles, extraction settings, AI runs telemetry.",
    "settings": "Per-user app settings.",
    "health": "Liveness and readiness probes.",
}

PATH_PARAM_TO_ENV = {
    "subject_id": "subject_id",
    "upload_id": "upload_id",
    "qs_id": "question_set_id",
    "question_set_id": "question_set_id",
    "question_id": "question_id",
    "user_id": "user_id",
    "session_id": "session_id",
    "notification_id": "notification_id",
    "prompt_id": "prompt_id",
    "credential_id": "credential_id",
    "model_id_param": "model_id",
    "model_id": "model_id",
    "profile_id": "profile_id",
    "run_id": "run_id",
    "choice_id": "choice_id",
}


def load_spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def deref(ref: str, spec: dict) -> dict:
    parts = ref.lstrip("#/").split("/")
    cur: dict = spec
    for p in parts:
        cur = cur[p]
    return cur


def schema_example(schema: dict, spec: dict, depth: int = 0) -> object:
    """Best-effort example value from a JSON schema."""
    if depth > 6:
        return None
    if not schema:
        return None
    if "$ref" in schema:
        return schema_example(deref(schema["$ref"], spec), spec, depth + 1)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if "anyOf" in schema:
        # Prefer the first non-null variant.
        for variant in schema["anyOf"]:
            if variant.get("type") != "null":
                return schema_example(variant, spec, depth + 1)
        return None
    if "oneOf" in schema:
        return schema_example(schema["oneOf"][0], spec, depth + 1)
    if "allOf" in schema:
        merged: dict = {"type": "object", "properties": {}, "required": []}
        for sub in schema["allOf"]:
            s = deref(sub["$ref"], spec) if "$ref" in sub else sub
            merged["properties"].update(s.get("properties", {}))
            merged["required"].extend(s.get("required", []))
        return schema_example(merged, spec, depth + 1)

    t = schema.get("type")
    if t == "object" or "properties" in schema:
        out = {}
        props = schema.get("properties", {})
        for name, sub in props.items():
            out[name] = schema_example(sub, spec, depth + 1)
        return out
    if t == "array":
        item = schema_example(schema.get("items", {}), spec, depth + 1)
        return [item] if item is not None else []
    if t == "integer":
        return 0
    if t == "number":
        return 0
    if t == "boolean":
        return False
    if t == "string":
        fmt = schema.get("format")
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "date":
            return "2026-01-01"
        if fmt == "email":
            return "student@example.com"
        if fmt == "binary":
            return ""
        return ""
    return None


def required_fields(schema: dict, spec: dict) -> list[str]:
    if not schema:
        return []
    if "$ref" in schema:
        return required_fields(deref(schema["$ref"], spec), spec)
    return list(schema.get("required", []) or [])


def schema_name(schema: dict) -> str | None:
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    return None


def path_to_postman(path: str) -> tuple[str, list[str]]:
    """Convert /api/v1/uploads/{upload_id}/events → /uploads/:upload_id/events.

    Returns (postman_path, [variable_names]).
    """
    # Strip /api/v1 prefix; keep /health as-is via a different base.
    stripped = path
    if stripped.startswith("/api/v1"):
        stripped = stripped[len("/api/v1"):]
    variables: list[str] = []

    def repl(match: re.Match) -> str:
        name = match.group(1)
        variables.append(name)
        return f":{name}"

    return re.sub(r"\{([^}]+)\}", repl, stripped), variables


def is_secured(op: dict) -> bool:
    # FastAPI emits `security: [{"HTTPBearer": []}]` for routes guarded by a
    # bearer dependency, and omits the field (None) on public routes.
    sec = op.get("security")
    return bool(sec)


def build_url(path: str, params_in_query: list[dict], spec: dict, is_health: bool) -> dict:
    pm_path, vars_ = path_to_postman(path)
    base_var = "root_url" if is_health else "base_url"
    segments = [s for s in pm_path.lstrip("/").split("/") if s != ""]
    url: dict = {
        "raw": "{{" + base_var + "}}" + pm_path,
        "host": ["{{" + base_var + "}}"],
        "path": segments,
    }
    if params_in_query:
        url["query"] = []
        for p in params_in_query:
            example = schema_example(p.get("schema", {}), spec)
            url["query"].append({
                "key": p["name"],
                "value": "" if example in (None, "") else str(example),
                "description": p.get("description", "") or "",
                "disabled": not p.get("required", False),
            })
        qstring = "&".join(f"{q['key']}={q['value']}" for q in url["query"] if not q.get("disabled"))
        if qstring:
            url["raw"] = url["raw"] + "?" + qstring
    if vars_:
        url["variable"] = []
        for v in vars_:
            env_key = PATH_PARAM_TO_ENV.get(v, v)
            url["variable"].append({
                "key": v,
                "value": "{{" + env_key + "}}",
                "description": f"Path variable :{v}",
            })
    return url


def build_body(op: dict, spec: dict) -> tuple[dict | None, list[str]]:
    """Returns (postman body block, list of required field names)."""
    rb = op.get("requestBody")
    if not rb:
        return None, []
    content = rb.get("content", {})
    json_ct = content.get("application/json")
    if not json_ct:
        # multipart / form-data — represent as formdata mode (mostly upload finalize/file paths).
        form_ct = content.get("multipart/form-data")
        if form_ct:
            schema = form_ct.get("schema", {})
            props = schema.get("properties", {})
            formdata = []
            for k, sub in props.items():
                if sub.get("format") == "binary":
                    formdata.append({"key": k, "type": "file", "src": []})
                else:
                    formdata.append({"key": k, "type": "text", "value": str(schema_example(sub, spec) or "")})
            return {"mode": "formdata", "formdata": formdata}, list(schema.get("required") or [])
        return None, []
    schema = json_ct.get("schema", {})
    example = schema_example(schema, spec) or {}
    body = {"mode": "raw", "raw": json.dumps(example, indent=2), "options": {"raw": {"language": "json"}}}
    return body, required_fields(schema, spec)


def describe_op(op: dict, spec: dict, required: list[str], body_schema_name: str | None,
                response_schema_name: str | None, secured: bool) -> str:
    parts = []
    summary = op.get("summary") or ""
    desc = op.get("description") or ""
    op_id = op.get("operationId") or ""
    if summary:
        parts.append(f"**{summary}**")
    if desc and desc.strip() and desc.strip() != summary.strip():
        parts.append(desc.strip())
    if op_id:
        parts.append(f"`operationId`: `{op_id}`")
    if secured:
        parts.append("**Requires:** Bearer token (`access_token`).")
    if required:
        parts.append("**Required body fields:** " + ", ".join(f"`{r}`" for r in required))
    if body_schema_name:
        parts.append(f"**Body schema:** `{body_schema_name}`")
    if response_schema_name:
        parts.append(f"**Response schema:** `{response_schema_name}`")
    return "\n\n".join(parts)


def response_schema_name(op: dict) -> str | None:
    for code in ("200", "201", "202"):
        resp = (op.get("responses") or {}).get(code)
        if not resp:
            continue
        content = resp.get("content", {}).get("application/json") or {}
        schema = content.get("schema") or {}
        if "$ref" in schema:
            return schema["$ref"].rsplit("/", 1)[-1]
        if schema.get("type") == "array" and "$ref" in (schema.get("items") or {}):
            return schema["items"]["$ref"].rsplit("/", 1)[-1] + "[]"
    return None


# ---- token-saving test scripts for auth ops -------------------------------

AUTH_SAVE_SCRIPT = {
    "listen": "test",
    "script": {
        "exec": [
            "const json = pm.response.json();",
            "if (json && json.access_token) {",
            "  pm.environment.set('access_token', json.access_token);",
            "  pm.environment.set('refresh_token', json.refresh_token);",
            "}",
        ],
        "type": "text/javascript",
    },
}


def build_item(method: str, path: str, op: dict, spec: dict) -> tuple[dict, str]:
    """Returns (postman item, markdown row)."""
    is_health = path.startswith("/health")
    # Split params by location.
    params = op.get("parameters") or []
    # Some params come from the path object itself — but we read from op; pyfastapi puts all params there.
    query_params = [p for p in params if p.get("in") == "query"]

    body, required = build_body(op, spec)
    body_schema = None
    if op.get("requestBody"):
        ct = op["requestBody"].get("content", {}).get("application/json")
        if ct:
            body_schema = schema_name(ct.get("schema") or {})
    resp_name = response_schema_name(op)
    secured = is_secured(op) and not is_health

    item: dict = {
        "name": op.get("summary") or op.get("operationId") or f"{method} {path}",
        "request": {
            "method": method,
            "header": [],
            "url": build_url(path, query_params, spec, is_health),
            "description": describe_op(op, spec, required, body_schema, resp_name, secured),
        },
        "response": [],
    }
    if secured:
        item["request"]["auth"] = {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}],
        }
    if body is not None:
        item["request"]["body"] = body
        item["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
    # Attach token-saving script for login/register/refresh.
    if op.get("operationId") in ("auth_login", "auth_register", "auth_refresh"):
        item["event"] = [AUTH_SAVE_SCRIPT]

    # Markdown row.
    pm_path, _ = path_to_postman(path)
    md_row = f"| `{method}` | `{pm_path}` | {op.get('summary') or op.get('operationId') or ''} | {'✓' if secured else ''} |"
    return item, md_row


def make_collection(tag: str, ops: list[tuple[str, str, dict]], spec: dict) -> dict:
    name = TAG_TO_NAME.get(tag, tag.title())
    desc = TAG_DESCRIPTION.get(tag, f"{name} endpoints.")
    items = []
    for method, path, op in ops:
        item, _ = build_item(method, path, op, spec)
        items.append(item)
    return {
        "info": {
            "_postman_id": f"a1b2c3d4-{abs(hash(tag)) % 10000:04d}-4000-8000-000000000000",
            "name": name,
            "description": desc,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }


def make_markdown(tag: str, ops: list[tuple[str, str, dict]], spec: dict) -> str:
    name = TAG_TO_NAME.get(tag, tag.title())
    desc = TAG_DESCRIPTION.get(tag, "")
    lines = [
        f"# {name}",
        "",
        desc,
        "",
        f"Postman collection: [{name}.postman_collection.json]({name}.postman_collection.json)",
        "",
        "## Endpoints",
        "",
        "| Method | Path | Summary | Auth |",
        "|---|---|---|---|",
    ]
    rows = []
    for method, path, op in ops:
        _, row = build_item(method, path, op, spec)
        rows.append(row)
    lines.extend(rows)
    lines.append("")
    lines.append("## Details")
    lines.append("")
    for method, path, op in ops:
        pm_path, _ = path_to_postman(path)
        op_id = op.get("operationId") or ""
        summary = op.get("summary") or op_id
        body, required = build_body(op, spec)
        body_schema = None
        if op.get("requestBody"):
            ct = op["requestBody"].get("content", {}).get("application/json")
            if ct:
                body_schema = schema_name(ct.get("schema") or {})
        resp_name = response_schema_name(op)
        params = op.get("parameters") or []
        path_params = [p for p in params if p.get("in") == "path"]
        query_params = [p for p in params if p.get("in") == "query"]
        secured = is_secured(op) and not path.startswith("/health")

        lines.append(f"### `{method}` `{pm_path}`")
        lines.append("")
        if summary:
            lines.append(f"_{summary}_")
            lines.append("")
        if op_id:
            lines.append(f"- **operationId:** `{op_id}`")
        if secured:
            lines.append("- **Auth:** Bearer token required")
        if path_params:
            lines.append("- **Path parameters:**")
            for p in path_params:
                lines.append(f"  - `{p['name']}` — {p.get('description','')}".rstrip())
        if query_params:
            lines.append("- **Query parameters:**")
            for p in query_params:
                req = " *(required)*" if p.get("required") else ""
                lines.append(f"  - `{p['name']}`{req} — {p.get('description','')}".rstrip())
        if body_schema:
            lines.append(f"- **Body:** `{body_schema}`" + (f" (required: {', '.join('`'+r+'`' for r in required)})" if required else ""))
        elif body is not None:
            lines.append("- **Body:** multipart/form-data")
        if resp_name:
            lines.append(f"- **Returns:** `{resp_name}`")
        desc_md = (op.get("description") or "").strip()
        if desc_md and desc_md != summary:
            lines.append("")
            lines.append(desc_md)
        lines.append("")
    lines.append("")
    lines.append("## Schemas referenced")
    lines.append("")
    seen = set()
    for method, path, op in ops:
        names = []
        if op.get("requestBody"):
            ct = op["requestBody"].get("content", {}).get("application/json")
            if ct:
                s = schema_name(ct.get("schema") or {})
                if s: names.append(s)
        r = response_schema_name(op)
        if r: names.append(r.rstrip("[]"))
        for n in names:
            if n and n not in seen:
                seen.add(n)
                lines.append(f"- `{n}`")
    lines.append("")
    lines.append("Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.")
    return "\n".join(lines)


def main() -> None:
    spec = load_spec()
    by_tag: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
    for path, methods in spec["paths"].items():
        for m, op in methods.items():
            if m not in ("get", "post", "put", "patch", "delete"):
                continue
            tag = (op.get("tags") or ["_untagged"])[0]
            by_tag[tag].append((m.upper(), path, op))

    # Stable ordering: by path then method.
    for tag in by_tag:
        by_tag[tag].sort(key=lambda r: (r[1], r[0]))

    written = []
    # Clean up superseded JSON files we're about to fully regenerate.
    for tag, ops in by_tag.items():
        name = TAG_TO_NAME.get(tag)
        if not name:
            print(f"[skip] unknown tag: {tag}")
            continue
        col = make_collection(tag, ops, spec)
        md = make_markdown(tag, ops, spec)
        (HERE / f"{name}.postman_collection.json").write_text(
            json.dumps(col, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (HERE / f"{name}.md").write_text(md + "\n", encoding="utf-8")
        written.append((name, len(ops)))

    print("Wrote:")
    for n, c in sorted(written):
        print(f"  {n:24} {c:3} endpoints")


if __name__ == "__main__":
    main()
