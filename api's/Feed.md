# Feed

Cross-subject feed of recent activity.

Postman collection: [Feed.postman_collection.json](Feed.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/feed` | Get Feed | ✓ |

## Details

### `GET` `/feed`

_Get Feed_

- **operationId:** `feed_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `page` —
  - `size` —
- **Returns:** `FeedListResponse`


## Schemas referenced

- `FeedListResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
