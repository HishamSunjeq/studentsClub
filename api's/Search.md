# Search

Cross-entity search.

Postman collection: [Search.postman_collection.json](Search.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/search` | Search | ✓ |

## Details

### `GET` `/search`

_Search_

- **operationId:** `search_query`
- **Auth:** Bearer token required
- **Query parameters:**
  - `q` — Search query
  - `limit` —
- **Returns:** `SearchResponse`


## Schemas referenced

- `SearchResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
