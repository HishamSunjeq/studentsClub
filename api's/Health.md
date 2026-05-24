# Health

Liveness and readiness probes.

Postman collection: [Health.postman_collection.json](Health.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/health` | Health |  |
| `GET` | `/health/ready` | Health Ready |  |

## Details

### `GET` `/health`

_Health_

- **operationId:** `health_health_get`

### `GET` `/health/ready`

_Health Ready_

- **operationId:** `health_ready_health_ready_get`


## Schemas referenced


Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
