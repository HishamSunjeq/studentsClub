# Admin

Admin control plane — prompts, credentials, models, profiles, extraction settings, AI runs telemetry.

Postman collection: [Admin.postman_collection.json](Admin.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/admin/ai/metrics` | Ai Metrics | ✓ |
| `GET` | `/admin/ai/runs` | List Ai Runs | ✓ |
| `GET` | `/admin/ai/runs/:run_id` | Get Ai Run | ✓ |
| `GET` | `/admin/credentials` | List Credentials | ✓ |
| `POST` | `/admin/credentials` | Create Credential | ✓ |
| `DELETE` | `/admin/credentials/:credential_id` | Delete Credential | ✓ |
| `PATCH` | `/admin/credentials/:credential_id` | Update Credential | ✓ |
| `POST` | `/admin/credentials/:credential_id/rotate` | Rotate Credential | ✓ |
| `POST` | `/admin/credentials/:credential_id/test` | Test Credential | ✓ |
| `GET` | `/admin/extraction` | Get Extraction Settings | ✓ |
| `PUT` | `/admin/extraction` | Update Extraction Settings | ✓ |
| `GET` | `/admin/models` | List Models | ✓ |
| `POST` | `/admin/models` | Create Model | ✓ |
| `DELETE` | `/admin/models/:model_id` | Delete Model | ✓ |
| `PATCH` | `/admin/models/:model_id` | Update Model | ✓ |
| `GET` | `/admin/profiles` | List Profiles | ✓ |
| `POST` | `/admin/profiles` | Create Profile | ✓ |
| `DELETE` | `/admin/profiles/:profile_id` | Delete Profile | ✓ |
| `PATCH` | `/admin/profiles/:profile_id` | Update Profile | ✓ |
| `GET` | `/admin/prompts` | List Prompts | ✓ |
| `POST` | `/admin/prompts` | Create Prompt | ✓ |
| `DELETE` | `/admin/prompts/:prompt_id` | Delete Prompt | ✓ |
| `POST` | `/admin/prompts/:prompt_id/activate` | Activate Prompt | ✓ |

## Details

### `GET` `/admin/ai/metrics`

_Ai Metrics_

- **operationId:** `admin_ai_metrics_get`
- **Auth:** Bearer token required
- **Query parameters:**
  - `range` —
- **Returns:** `AIMetricsResponse`

### `GET` `/admin/ai/runs`

_List Ai Runs_

- **operationId:** `admin_ai_runs_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `question_set_id` —
  - `provider` —
  - `model` —
  - `credential_alias` —
  - `status` —
  - `since` —
  - `until` —
  - `page` —
  - `size` —
- **Returns:** `AIRunListResponse`

### `GET` `/admin/ai/runs/:run_id`

_Get Ai Run_

- **operationId:** `admin_ai_runs_get`
- **Auth:** Bearer token required
- **Path parameters:**
  - `run_id` —
- **Returns:** `AIRunDetailResponse`

### `GET` `/admin/credentials`

_List Credentials_

- **operationId:** `admin_credentials_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `provider` —
- **Returns:** `CredentialListResponse`

### `POST` `/admin/credentials`

_Create Credential_

- **operationId:** `admin_credentials_create`
- **Auth:** Bearer token required
- **Body:** `CredentialCreateRequest` (required: `alias`, `provider`, `api_key`)
- **Returns:** `CredentialResponse`

### `DELETE` `/admin/credentials/:credential_id`

_Delete Credential_

- **operationId:** `admin_credentials_delete`
- **Auth:** Bearer token required
- **Path parameters:**
  - `credential_id` —

### `PATCH` `/admin/credentials/:credential_id`

_Update Credential_

- **operationId:** `admin_credentials_update`
- **Auth:** Bearer token required
- **Path parameters:**
  - `credential_id` —
- **Body:** `CredentialUpdateRequest`
- **Returns:** `CredentialResponse`

### `POST` `/admin/credentials/:credential_id/rotate`

_Rotate Credential_

- **operationId:** `admin_credentials_rotate`
- **Auth:** Bearer token required
- **Path parameters:**
  - `credential_id` —
- **Body:** `CredentialRotateRequest` (required: `api_key`)
- **Returns:** `CredentialResponse`

### `POST` `/admin/credentials/:credential_id/test`

_Test Credential_

- **operationId:** `admin_credentials_test`
- **Auth:** Bearer token required
- **Path parameters:**
  - `credential_id` —
- **Returns:** `CredentialTestResponse`

Dry-run the credential against its provider with a 1-token call.
Never returns the plaintext key in errors.

### `GET` `/admin/extraction`

_Get Extraction Settings_

- **operationId:** `admin_extraction_get`
- **Auth:** Bearer token required
- **Returns:** `ExtractionSettingsResponse`

### `PUT` `/admin/extraction`

_Update Extraction Settings_

- **operationId:** `admin_extraction_update`
- **Auth:** Bearer token required
- **Body:** `ExtractionSettingsUpdateRequest`
- **Returns:** `ExtractionSettingsResponse`

### `GET` `/admin/models`

_List Models_

- **operationId:** `admin_models_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `kind` —
  - `provider` —
- **Returns:** `ModelListResponse`

### `POST` `/admin/models`

_Create Model_

- **operationId:** `admin_models_create`
- **Auth:** Bearer token required
- **Body:** `ModelCreateRequest` (required: `provider`, `model_id`, `display_name`, `kind`)
- **Returns:** `ModelResponse`

### `DELETE` `/admin/models/:model_id`

_Delete Model_

- **operationId:** `admin_models_delete`
- **Auth:** Bearer token required
- **Path parameters:**
  - `model_id` —

### `PATCH` `/admin/models/:model_id`

_Update Model_

- **operationId:** `admin_models_update`
- **Auth:** Bearer token required
- **Path parameters:**
  - `model_id` —
- **Body:** `ModelUpdateRequest`
- **Returns:** `ModelResponse`

### `GET` `/admin/profiles`

_List Profiles_

- **operationId:** `admin_profiles_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `subject_id` —
- **Returns:** `ProfileListResponse`

### `POST` `/admin/profiles`

_Create Profile_

- **operationId:** `admin_profiles_create`
- **Auth:** Bearer token required
- **Body:** `ProfileCreateRequest` (required: `name`)
- **Returns:** `ProfileResponse`

### `DELETE` `/admin/profiles/:profile_id`

_Delete Profile_

- **operationId:** `admin_profiles_delete`
- **Auth:** Bearer token required
- **Path parameters:**
  - `profile_id` —

### `PATCH` `/admin/profiles/:profile_id`

_Update Profile_

- **operationId:** `admin_profiles_update`
- **Auth:** Bearer token required
- **Path parameters:**
  - `profile_id` —
- **Body:** `ProfileUpdateRequest`
- **Returns:** `ProfileResponse`

### `GET` `/admin/prompts`

_List Prompts_

- **operationId:** `admin_prompts_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `name` —
- **Returns:** `PromptListResponse`

### `POST` `/admin/prompts`

_Create Prompt_

- **operationId:** `admin_prompts_create`
- **Auth:** Bearer token required
- **Body:** `PromptCreateRequest` (required: `name`, `content`)
- **Returns:** `PromptResponse`

### `DELETE` `/admin/prompts/:prompt_id`

_Delete Prompt_

- **operationId:** `admin_prompts_delete`
- **Auth:** Bearer token required
- **Path parameters:**
  - `prompt_id` —

### `POST` `/admin/prompts/:prompt_id/activate`

_Activate Prompt_

- **operationId:** `admin_prompts_activate`
- **Auth:** Bearer token required
- **Path parameters:**
  - `prompt_id` —
- **Returns:** `PromptResponse`


## Schemas referenced

- `AIMetricsResponse`
- `AIRunListResponse`
- `AIRunDetailResponse`
- `CredentialListResponse`
- `CredentialCreateRequest`
- `CredentialResponse`
- `CredentialUpdateRequest`
- `CredentialRotateRequest`
- `CredentialTestResponse`
- `ExtractionSettingsResponse`
- `ExtractionSettingsUpdateRequest`
- `ModelListResponse`
- `ModelCreateRequest`
- `ModelResponse`
- `ModelUpdateRequest`
- `ProfileListResponse`
- `ProfileCreateRequest`
- `ProfileResponse`
- `ProfileUpdateRequest`
- `PromptListResponse`
- `PromptCreateRequest`
- `PromptResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
