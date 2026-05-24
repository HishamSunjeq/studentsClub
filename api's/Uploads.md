# Uploads

File uploads — presigned PUT flow, finalize, listing, generation kickoff, SSE stream.

Postman collection: [Uploads.postman_collection.json](Uploads.postman_collection.json)

## Endpoints

| Method | Path | Summary | Auth |
|---|---|---|---|
| `GET` | `/uploads` | List Uploads | ✓ |
| `POST` | `/uploads` | Create Upload | ✓ |
| `DELETE` | `/uploads/:upload_id` | Delete Upload | ✓ |
| `GET` | `/uploads/:upload_id` | Get Upload | ✓ |
| `PATCH` | `/uploads/:upload_id` | Update Upload | ✓ |
| `GET` | `/uploads/:upload_id/events` | Stream Upload Events |  |
| `POST` | `/uploads/:upload_id/finalize` | Finalize Upload | ✓ |
| `POST` | `/uploads/:upload_id/generate` | Generate Questions | ✓ |
| `GET` | `/uploads/:upload_id/generation-defaults` | Generation Defaults | ✓ |
| `GET` | `/uploads/:upload_id/preview-url` | Get Preview Url | ✓ |

## Details

### `GET` `/uploads`

_List Uploads_

- **operationId:** `uploads_list`
- **Auth:** Bearer token required
- **Query parameters:**
  - `status` —
  - `subject_id` —
  - `page` —
  - `size` —
- **Returns:** `UploadListResponse`

### `POST` `/uploads`

_Create Upload_

- **operationId:** `uploads_create`
- **Auth:** Bearer token required
- **Body:** `UploadCreateRequest` (required: `filename`, `content_type`, `size_bytes`)
- **Returns:** `PresignResponse`

### `DELETE` `/uploads/:upload_id`

_Delete Upload_

- **operationId:** `uploads_delete`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —

### `GET` `/uploads/:upload_id`

_Get Upload_

- **operationId:** `uploads_get`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —
- **Returns:** `UploadDetailResponse`

### `PATCH` `/uploads/:upload_id`

_Update Upload_

- **operationId:** `uploads_update`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —
- **Body:** `UploadUpdateRequest`
- **Returns:** `UploadResponse`

### `GET` `/uploads/:upload_id/events`

_Stream Upload Events_

- **operationId:** `uploads_events`
- **Path parameters:**
  - `upload_id` —
- **Query parameters:**
  - `token` *(required)* — Access JWT (EventSource cannot set headers)

### `POST` `/uploads/:upload_id/finalize`

_Finalize Upload_

- **operationId:** `uploads_finalize`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —
- **Returns:** `UploadResponse`

### `POST` `/uploads/:upload_id/generate`

_Generate Questions_

- **operationId:** `uploads_generate`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —
- **Body:** `GenerateRequest`
- **Returns:** `GenerateResponse`

### `GET` `/uploads/:upload_id/generation-defaults`

_Generation Defaults_

- **operationId:** `uploads_generation_defaults`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —
- **Returns:** `GenerationDefaultsResponse`

### `GET` `/uploads/:upload_id/preview-url`

_Get Preview Url_

- **operationId:** `uploads_preview_url`
- **Auth:** Bearer token required
- **Path parameters:**
  - `upload_id` —
- **Returns:** `PreviewUrlResponse`


## Schemas referenced

- `UploadListResponse`
- `UploadCreateRequest`
- `PresignResponse`
- `UploadDetailResponse`
- `UploadUpdateRequest`
- `UploadResponse`
- `GenerateRequest`
- `GenerateResponse`
- `GenerationDefaultsResponse`
- `PreviewUrlResponse`

Full schemas live in the OpenAPI spec at `http://localhost:8000/openapi.json` and in `frontend/apps/web/src/api/generated/schemas/`.
