# Notifications

Notification inbox — list, mark read, mark all read.

Postman collection: [Notifications.postman_collection.json](Notifications.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/notifications` | List Notifications | ✓ |
| `POST` | `/notifications/read-all` | Mark All Read | ✓ |
| `POST` | `/notifications/:notification_id/read` | Mark Read | ✓ |

## Details

### `GET` `/notifications`

_List Notifications_

- **operationId:** `notifications_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `page` —
  - `size` —
  - `unread_only` —
- **Returns:** `NotificationListResponse`

### `POST` `/notifications/read-all`

_Mark All Read_

- **operationId:** `notifications_mark_all_read`
- **Auth:** Bearer token required

### `POST` `/notifications/:notification_id/read`

_Mark Read_

- **operationId:** `notifications_mark_read`
- **Auth:** Bearer token required
- **Path parameters:**
  - `notification_id` —
- **Returns:** `NotificationResponse`


## Schemas referenced

- `NotificationListResponse`
- `NotificationResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
