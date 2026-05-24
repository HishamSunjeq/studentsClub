# Subject_Chat

Per-subject RAG-grounded Q&A chat. Sessions, message history, SSE event stream.

Postman collection: [Subject_Chat.postman_collection.json](Subject_Chat.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/subjects/:subject_id/chat/sessions` | List Sessions | ✓ |
| `POST` | `/subjects/:subject_id/chat/sessions` | Create Session | ✓ |
| `GET` | `/subjects/:subject_id/chat/sessions/:session_id/events` | Stream Chat Events |  |
| `GET` | `/subjects/:subject_id/chat/sessions/:session_id/messages` | List Messages | ✓ |
| `POST` | `/subjects/:subject_id/chat/sessions/:session_id/messages` | Send Message | ✓ |

## Details

### `GET` `/subjects/:subject_id/chat/sessions`

_List Sessions_

- **operationId:** `subject_chat_sessions_list`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —
- **Returns:** `ChatSessionListResponse`

### `POST` `/subjects/:subject_id/chat/sessions`

_Create Session_

- **operationId:** `subject_chat_sessions_create`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —
- **Body:** `ChatSessionCreateRequest`
- **Returns:** `ChatSessionResponse`

### `GET` `/subjects/:subject_id/chat/sessions/:session_id/events`

_Stream Chat Events_

- **operationId:** `subject_chat_events`
- **Path parameters:**
  - `subject_id` —
  - `session_id` —
- **Query parameters:**
  - `token` *(required)* — Access JWT (EventSource cannot set headers)

### `GET` `/subjects/:subject_id/chat/sessions/:session_id/messages`

_List Messages_

- **operationId:** `subject_chat_messages_list`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —
  - `session_id` —
- **Returns:** `ChatMessageListResponse`

### `POST` `/subjects/:subject_id/chat/sessions/:session_id/messages`

_Send Message_

- **operationId:** `subject_chat_send`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —
  - `session_id` —
- **Body:** `ChatSendRequest` (required: `content`)
- **Returns:** `ChatSendResponse`


## Schemas referenced

- `ChatSessionListResponse`
- `ChatSessionCreateRequest`
- `ChatSessionResponse`
- `ChatMessageListResponse`
- `ChatSendRequest`
- `ChatSendResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
