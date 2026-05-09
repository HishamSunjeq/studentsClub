import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.tasks.process_upload import run as process_upload_task

REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "password123",
    "full_name": "Alice Smith",
    "college": "Engineering",
    "academic_year": 2,
}

VALID_UPLOAD = {
    "filename": "lecture_notes.pdf",
    "content_type": "application/pdf",
    "size_bytes": 1024 * 100,  # 100 KB
}


async def _register_and_token(client: AsyncClient) -> str:
    r = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    return r.json()["access_token"]


@pytest.fixture(autouse=True)
def mock_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.uploads_service.storage_service.generate_presigned_put_url",
        lambda key, ct, expires_in=900: f"https://fake-s3.local/{key}",
    )
    monkeypatch.setattr(
        process_upload_task,
        "delay",
        lambda *a, **k: None,
    )


class TestCreateUpload:
    async def test_create_success(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json=VALID_UPLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        body = r.json()
        assert "upload_id" in body
        assert "presigned_url" in body
        assert body["presigned_url"].startswith("https://fake-s3.local/uploads/")
        assert body["s3_key"].endswith("lecture_notes.pdf")

    async def test_create_requires_auth(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/uploads", json=VALID_UPLOAD)
        assert r.status_code == 401

    async def test_invalid_content_type(self, client: AsyncClient) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json={**VALID_UPLOAD, "content_type": "text/plain"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    async def test_file_too_large(self, client: AsyncClient) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json={**VALID_UPLOAD, "size_bytes": 999_999_999},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    async def test_docx_allowed(self, client: AsyncClient) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json={
                "filename": "notes.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size_bytes": 2048,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201


class TestFinalizeUpload:
    async def _create_upload(self, client: AsyncClient, token: str) -> str:
        r = await client.post(
            "/api/v1/uploads",
            json=VALID_UPLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        return r.json()["upload_id"]

    async def test_finalize_success(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        upload_id = await self._create_upload(client, token)

        r = await client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "extracting"
        assert body["finalized_at"] is not None

    async def test_finalize_twice_returns_409(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        upload_id = await self._create_upload(client, token)
        await client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = await client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409

    async def test_finalize_unknown_returns_404(self, client: AsyncClient) -> None:
        import uuid
        token = await _register_and_token(client)
        r = await client.post(
            f"/api/v1/uploads/{uuid.uuid4()}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    async def test_finalize_requires_auth(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        upload_id = await self._create_upload(client, token)
        r = await client.post(f"/api/v1/uploads/{upload_id}/finalize")
        assert r.status_code == 401

    async def test_finalize_wrong_user_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        upload_id = await self._create_upload(client, token)

        r2 = await client.post(
            "/api/v1/auth/register",
            json={**REGISTER_PAYLOAD, "email": "bob@example.com"},
        )
        other_token = r2.json()["access_token"]

        r = await client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert r.status_code == 403


class TestGetUpload:
    async def test_get_pending(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json=VALID_UPLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        upload_id = r.json()["upload_id"]

        r2 = await client.get(
            f"/api/v1/uploads/{upload_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "pending"

    async def test_get_finalized(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json=VALID_UPLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        upload_id = r.json()["upload_id"]
        await client.post(
            f"/api/v1/uploads/{upload_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        r2 = await client.get(
            f"/api/v1/uploads/{upload_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.json()["status"] == "extracting"

    async def test_get_wrong_user_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        r = await client.post(
            "/api/v1/uploads",
            json=VALID_UPLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        upload_id = r.json()["upload_id"]

        r2 = await client.post(
            "/api/v1/auth/register",
            json={**REGISTER_PAYLOAD, "email": "eve@example.com"},
        )
        other_token = r2.json()["access_token"]

        r3 = await client.get(
            f"/api/v1/uploads/{upload_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert r3.status_code == 403

    async def test_get_requires_auth(self, client: AsyncClient, db: AsyncSession) -> None:
        import uuid
        r = await client.get(f"/api/v1/uploads/{uuid.uuid4()}")
        assert r.status_code == 401
