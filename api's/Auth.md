# Auth

Authentication endpoints — register, login, refresh, logout, change/forgot/reset password.

Postman collection: [Auth.postman_collection.json](Auth.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `POST` | `/auth/change-password` | Change Password | ✓ |
| `POST` | `/auth/forgot-password` | Forgot Password |  |
| `POST` | `/auth/login` | Login |  |
| `POST` | `/auth/logout` | Logout |  |
| `POST` | `/auth/refresh` | Refresh |  |
| `POST` | `/auth/register` | Register |  |
| `POST` | `/auth/reset-password` | Reset Password |  |

## Details

### `POST` `/auth/change-password`

_Change Password_

- **operationId:** `auth_change_password`
- **Auth:** Bearer token required
- **Body:** `ChangePasswordRequest` (required: `current_password`, `new_password`)

### `POST` `/auth/forgot-password`

_Forgot Password_

- **operationId:** `auth_forgot_password`
- **Body:** `ForgotPasswordRequest` (required: `email`)

### `POST` `/auth/login`

_Login_

- **operationId:** `auth_login`
- **Body:** `LoginRequest` (required: `email`, `password`)
- **Returns:** `TokenResponse`

### `POST` `/auth/logout`

_Logout_

- **operationId:** `auth_logout`
- **Body:** `LogoutRequest` (required: `refresh_token`)

### `POST` `/auth/refresh`

_Refresh_

- **operationId:** `auth_refresh`
- **Body:** `RefreshRequest` (required: `refresh_token`)
- **Returns:** `TokenResponse`

### `POST` `/auth/register`

_Register_

- **operationId:** `auth_register`
- **Body:** `RegisterRequest` (required: `email`, `password`, `full_name`, `college`, `academic_year`)
- **Returns:** `TokenResponse`

### `POST` `/auth/reset-password`

_Reset Password_

- **operationId:** `auth_reset_password`
- **Body:** `ResetPasswordRequest` (required: `token`, `new_password`)


## Schemas referenced

- `ChangePasswordRequest`
- `ForgotPasswordRequest`
- `LoginRequest`
- `TokenResponse`
- `LogoutRequest`
- `RefreshRequest`
- `RegisterRequest`
- `ResetPasswordRequest`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
