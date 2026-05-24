# Questions

Per-question edit, deactivate, regenerate with RAG context, retrieval preview.

Postman collection: [Questions.postman_collection.json](Questions.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `DELETE` | `/questions/:question_id` | Deactivate Question | ✓ |
| `PATCH` | `/questions/:question_id` | Update Question | ✓ |
| `POST` | `/questions/:question_id/regenerate` | Regenerate Question | ✓ |
| `GET` | `/questions/:question_id/retrieval-preview` | Retrieval Preview | ✓ |

## Details

### `DELETE` `/questions/:question_id`

_Deactivate Question_

- **operationId:** `questions_deactivate`
- **Auth:** Bearer token required
- **Path parameters:**
  - `question_id` —

### `PATCH` `/questions/:question_id`

_Update Question_

- **operationId:** `questions_update`
- **Auth:** Bearer token required
- **Path parameters:**
  - `question_id` —
- **Body:** `QuestionUpdateRequest`
- **Returns:** `QuestionResponse`

### `POST` `/questions/:question_id/regenerate`

_Regenerate Question_

- **operationId:** `questions_regenerate`
- **Auth:** Bearer token required
- **Path parameters:**
  - `question_id` —
- **Body:** multipart/form-data
- **Returns:** `QuestionResponse`

### `GET` `/questions/:question_id/retrieval-preview`

_Retrieval Preview_

- **operationId:** `questions_retrieval_preview`
- **Auth:** Bearer token required
- **Path parameters:**
  - `question_id` —
- **Returns:** `RetrievalPreviewResponse`


## Schemas referenced

- `QuestionUpdateRequest`
- `QuestionResponse`
- `RetrievalPreviewResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
