# Postman collections

Hand-maintained Postman collections for manual API exploration. These are **supplementary** — the source of truth is the live OpenAPI spec at `http://localhost:8000/openapi.json` (or `/docs` for Swagger UI).

> The folder name `api's` is a historical typo and will be renamed in a future commit. Imports that depend on the path should be updated then.

## Files

| Collection | Covers |
|---|---|
| `Auth.postman_collection.json` | Register, login, refresh, logout |
| `Subjects.postman_collection.json` | Catalogue, enrol, unenrol |
| `Uploads.postman_collection.json` | Create upload, presigned PUT, finalize, generation |
| `Question_Sets.postman_collection.json` | Draft review, publish, reject, replay |
| `Questions.postman_collection.json` | Per-question edit / regenerate |
| `Quizzes.postman_collection.json` | Quiz session start, submit answers |
| `Feed.postman_collection.json` | Subject feed |
| `Notifications.postman_collection.json` | List, mark read |
| `Users.postman_collection.json` | Profile, stats |
| `Search.postman_collection.json` | Cross-entity search |
| `StudentsClub.postman_environment.json` | Environment variables (base URL, tokens) |

## Usage

1. Import the environment file and all collections into Postman.
2. Run `Auth → Login` first; the response saves `access_token` into the environment.
3. Other requests rely on `{{access_token}}` as their Authorization header.

The backend must be running locally (`docker compose up`) on the URL configured in the environment.
