# Question_Sets

Draft review, publish/reject, replay against a different prompt/model/profile.

Postman collection: [Question_Sets.postman_collection.json](Question_Sets.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/question-sets/me` | List My Question Sets | ✓ |
| `GET` | `/question-sets/:qs_id` | Get Question Set | ✓ |
| `PATCH` | `/question-sets/:qs_id` | Update Question Set | ✓ |
| `POST` | `/question-sets/:qs_id/publish` | Publish Question Set | ✓ |
| `POST` | `/question-sets/:qs_id/reject` | Reject Question Set | ✓ |
| `POST` | `/question-sets/:qs_id/replay` | Replay Question Set | ✓ |

## Details

### `GET` `/question-sets/me`

_List My Question Sets_

- **operationId:** `question_sets_list_mine`
- **Auth:** Bearer token required
- **Query parameters:**
  - `status` —
  - `page` —
  - `size` —
- **Returns:** `QuestionSetListResponse`

### `GET` `/question-sets/:qs_id`

_Get Question Set_

- **operationId:** `question_sets_get`
- **Auth:** Bearer token required
- **Path parameters:**
  - `qs_id` —
- **Returns:** `QuestionSetWithQuestionsResponse`

### `PATCH` `/question-sets/:qs_id`

_Update Question Set_

- **operationId:** `question_sets_update`
- **Auth:** Bearer token required
- **Path parameters:**
  - `qs_id` —
- **Body:** `QuestionSetUpdateRequest` (required: `title`)
- **Returns:** `QuestionSetResponse`

### `POST` `/question-sets/:qs_id/publish`

_Publish Question Set_

- **operationId:** `question_sets_publish`
- **Auth:** Bearer token required
- **Path parameters:**
  - `qs_id` —
- **Returns:** `QuestionSetResponse`

### `POST` `/question-sets/:qs_id/reject`

_Reject Question Set_

- **operationId:** `question_sets_reject`
- **Auth:** Bearer token required
- **Path parameters:**
  - `qs_id` —
- **Returns:** `QuestionSetResponse`

### `POST` `/question-sets/:qs_id/replay`

_Replay Question Set_

- **operationId:** `question_sets_replay`
- **Auth:** Bearer token required
- **Path parameters:**
  - `qs_id` —
- **Body:** `QuestionSetReplayRequest`
- **Returns:** `QuestionSetResponse`


## Schemas referenced

- `QuestionSetListResponse`
- `QuestionSetWithQuestionsResponse`
- `QuestionSetUpdateRequest`
- `QuestionSetResponse`
- `QuestionSetReplayRequest`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
