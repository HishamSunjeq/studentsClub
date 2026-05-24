# Subjects

Subject catalogue, enrolment, members, top contributors, published question sets, leaderboard.

Postman collection: [Subjects.postman_collection.json](Subjects.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/subjects` | List Subjects |  |
| `GET` | `/subjects/me` | My Subjects | ✓ |
| `GET` | `/subjects/:subject_id` | Get Subject |  |
| `DELETE` | `/subjects/:subject_id/enroll` | Unenroll | ✓ |
| `POST` | `/subjects/:subject_id/enroll` | Enroll | ✓ |
| `GET` | `/subjects/:subject_id/leaderboard` | Get Leaderboard | ✓ |
| `GET` | `/subjects/:subject_id/members` | Get Members |  |
| `GET` | `/subjects/:subject_id/question-sets` | Get Published Sets |  |
| `GET` | `/subjects/:subject_id/top-contributors` | Get Top Contributors |  |

## Details

### `GET` `/subjects`

_List Subjects_

- **operationId:** `subjects_list`
- **Query parameters:**
  - `college` —
  - `academic_year` —
  - `page` —
  - `size` —
- **Returns:** `SubjectListResponse`

### `GET` `/subjects/me`

_My Subjects_

- **operationId:** `subjects_list_mine`
- **Auth:** Bearer token required
- **Query parameters:**
  - `page` —
  - `size` —
- **Returns:** `SubjectListResponse`

### `GET` `/subjects/:subject_id`

_Get Subject_

- **operationId:** `subjects_get`
- **Path parameters:**
  - `subject_id` —
- **Returns:** `SubjectResponse`

### `DELETE` `/subjects/:subject_id/enroll`

_Unenroll_

- **operationId:** `subjects_unenroll`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —

### `POST` `/subjects/:subject_id/enroll`

_Enroll_

- **operationId:** `subjects_enroll`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —
- **Returns:** `EnrollmentResponse`

### `GET` `/subjects/:subject_id/leaderboard`

_Get Leaderboard_

- **operationId:** `subjects_get_leaderboard`
- **Auth:** Bearer token required
- **Path parameters:**
  - `subject_id` —
- **Query parameters:**
  - `limit` —
- **Returns:** `SubjectLeaderboardEntry[]`

### `GET` `/subjects/:subject_id/members`

_Get Members_

- **operationId:** `subjects_get_members`
- **Path parameters:**
  - `subject_id` —
- **Query parameters:**
  - `page` —
  - `size` —
- **Returns:** `SubjectMemberListResponse`

### `GET` `/subjects/:subject_id/question-sets`

_Get Published Sets_

- **operationId:** `subjects_get_published_sets`
- **Path parameters:**
  - `subject_id` —
- **Query parameters:**
  - `page` —
  - `size` —
- **Returns:** `SubjectPublishedSetListResponse`

### `GET` `/subjects/:subject_id/top-contributors`

_Get Top Contributors_

- **operationId:** `subjects_get_top_contributors`
- **Path parameters:**
  - `subject_id` —
- **Query parameters:**
  - `limit` —
- **Returns:** `SubjectContributorResponse[]`


## Schemas referenced

- `SubjectListResponse`
- `SubjectResponse`
- `EnrollmentResponse`
- `SubjectLeaderboardEntry`
- `SubjectMemberListResponse`
- `SubjectPublishedSetListResponse`
- `SubjectContributorResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
