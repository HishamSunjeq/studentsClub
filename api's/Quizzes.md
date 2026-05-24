# Quizzes

Quiz sessions: start, answer, complete, list, fetch result.

Postman collection: [Quizzes.postman_collection.json](Quizzes.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `POST` | `/quizzes` | Start Quiz | ✓ |
| `GET` | `/quizzes/me` | List My Quizzes | ✓ |
| `GET` | `/quizzes/:session_id` | Get Quiz | ✓ |
| `POST` | `/quizzes/:session_id/answer` | Submit Answer | ✓ |
| `POST` | `/quizzes/:session_id/complete` | Complete Quiz | ✓ |
| `GET` | `/quizzes/:session_id/questions` | Get Quiz With Questions | ✓ |
| `GET` | `/quizzes/:session_id/result` | Get Quiz Result | ✓ |

## Details

### `POST` `/quizzes`

_Start Quiz_

- **operationId:** `quizzes_start`
- **Auth:** Bearer token required
- **Body:** `QuizStartRequest` (required: `subject_id`)
- **Returns:** `QuizSessionWithQuestionsResponse`

### `GET` `/quizzes/me`

_List My Quizzes_

- **operationId:** `quizzes_list_mine`
- **Auth:** Bearer token required
- **Query parameters:**
  - `page` —
  - `size` —
  - `status` —
  - `subject_id` —
- **Returns:** `QuizSessionListResponse`

### `GET` `/quizzes/:session_id`

_Get Quiz_

- **operationId:** `quizzes_get`
- **Auth:** Bearer token required
- **Path parameters:**
  - `session_id` —
- **Returns:** `QuizSessionResponse`

### `POST` `/quizzes/:session_id/answer`

_Submit Answer_

- **operationId:** `quizzes_submit_answer`
- **Auth:** Bearer token required
- **Path parameters:**
  - `session_id` —
- **Body:** `QuizAnswerRequest` (required: `question_id`, `choice_id`)
- **Returns:** `QuizAnswerResponse`

### `POST` `/quizzes/:session_id/complete`

_Complete Quiz_

- **operationId:** `quizzes_complete`
- **Auth:** Bearer token required
- **Path parameters:**
  - `session_id` —
- **Returns:** `QuizSessionResponse`

### `GET` `/quizzes/:session_id/questions`

_Get Quiz With Questions_

- **operationId:** `quizzes_get_with_questions`
- **Auth:** Bearer token required
- **Path parameters:**
  - `session_id` —
- **Returns:** `QuizSessionWithQuestionsResponse`

### `GET` `/quizzes/:session_id/result`

_Get Quiz Result_

- **operationId:** `quizzes_get_result`
- **Auth:** Bearer token required
- **Path parameters:**
  - `session_id` —
- **Returns:** `QuizResultResponse`


## Schemas referenced

- `QuizStartRequest`
- `QuizSessionWithQuestionsResponse`
- `QuizSessionListResponse`
- `QuizSessionResponse`
- `QuizAnswerRequest`
- `QuizAnswerResponse`
- `QuizResultResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
