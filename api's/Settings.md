# Settings

Per-user app settings.

Postman collection: [Settings.postman_collection.json](Settings.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/users/me/settings` | Get My Settings | ✓ |
| `PATCH` | `/users/me/settings` | Update My Settings | ✓ |

## Details

### `GET` `/users/me/settings`

_Get My Settings_

- **operationId:** `settings_get`
- **Auth:** Bearer token required
- **Returns:** `UserSettingsResponse`

### `PATCH` `/users/me/settings`

_Update My Settings_

- **operationId:** `settings_update`
- **Auth:** Bearer token required
- **Body:** `UserSettingsUpdate`
- **Returns:** `UserSettingsResponse`


## Schemas referenced

- `UserSettingsResponse`
- `UserSettingsUpdate`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
