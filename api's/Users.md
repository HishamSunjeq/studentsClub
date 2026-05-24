# Users

Current-user profile, stats, continue-watching, recommended subjects, and public profile lookup.

Postman collection: [Users.postman_collection.json](Users.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/users/me` | Get Me | ✓ |
| `GET` | `/users/me/continue` | Get My Continue | ✓ |
| `GET` | `/users/me/recommended-subjects` | Get My Recommended Subjects | ✓ |
| `GET` | `/users/me/stats` | Get My Stats | ✓ |
| `GET` | `/users/:user_id/profile` | Get User Profile | ✓ |

## Details

### `GET` `/users/me`

_Get Me_

- **operationId:** `users_get_me`
- **Auth:** Bearer token required
- **Returns:** `UserResponse`

### `GET` `/users/me/continue`

_Get My Continue_

- **operationId:** `users_get_me_continue`
- **Auth:** Bearer token required

### `GET` `/users/me/recommended-subjects`

_Get My Recommended Subjects_

- **operationId:** `users_get_me_recommended_subjects`
- **Auth:** Bearer token required
- **Returns:** `RecommendedSubjectItem[]`

### `GET` `/users/me/stats`

_Get My Stats_

- **operationId:** `users_get_me_stats`
- **Auth:** Bearer token required
- **Returns:** `UserStatsResponse`

### `GET` `/users/:user_id/profile`

_Get User Profile_

- **operationId:** `users_get_profile`
- **Auth:** Bearer token required
- **Path parameters:**
  - `user_id` —
- **Returns:** `UserProfileResponse`


## Schemas referenced

- `UserResponse`
- `RecommendedSubjectItem`
- `UserStatsResponse`
- `UserProfileResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
