# Chunks

Look up document chunk excerpts by IDs (used by citation popovers).

Postman collection: [Chunks.postman_collection.json](Chunks.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/chunks` | Get Chunks | ✓ |

## Details

### `GET` `/chunks`

_Get Chunks_

- **operationId:** `chunks_by_ids`
- **Auth:** Bearer token required
- **Query parameters:**
  - `ids` *(required)* — Comma-separated chunk UUIDs
- **Returns:** `ChunkListResponse`


## Schemas referenced

- `ChunkListResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
