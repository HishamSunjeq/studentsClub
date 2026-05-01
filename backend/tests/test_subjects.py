import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject

REGISTER_PAYLOAD = {
    "email": "bob@example.com",
    "password": "password123",
    "full_name": "Bob Jones",
    "college": "Engineering",
    "academic_year": 2,
}

SUBJECT_A = {
    "name": "Data Structures",
    "code": "CS201",
    "college": "Engineering",
    "academic_year": 2,
}
SUBJECT_B = {
    "name": "Operating Systems",
    "code": "CS301",
    "college": "Engineering",
    "academic_year": 3,
}
SUBJECT_C = {
    "name": "Anatomy I",
    "code": "MED101",
    "college": "Medicine",
    "academic_year": 1,
}


async def _seed_subjects(db: AsyncSession) -> list[Subject]:
    subjects = [Subject(**SUBJECT_A), Subject(**SUBJECT_B), Subject(**SUBJECT_C)]
    for s in subjects:
        db.add(s)
    await db.flush()
    return subjects


async def _register_and_token(client: AsyncClient) -> str:
    r = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    return r.json()["access_token"]


class TestListSubjects:
    async def test_list_all(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        r = await client.get("/api/v1/subjects")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    async def test_filter_by_college(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        r = await client.get("/api/v1/subjects", params={"college": "Engineering"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert all(s["college"] == "Engineering" for s in body["items"])

    async def test_filter_by_academic_year(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        r = await client.get("/api/v1/subjects", params={"academic_year": 2})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["code"] == "CS201"

    async def test_filter_by_college_and_year(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        r = await client.get(
            "/api/v1/subjects", params={"college": "Engineering", "academic_year": 3}
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1

    async def test_pagination(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        r = await client.get("/api/v1/subjects", params={"page": 1, "size": 2})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["pages"] == 2

    async def test_list_no_auth_required(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        r = await client.get("/api/v1/subjects")
        assert r.status_code == 200


class TestGetSubject:
    async def test_get_subject_success(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        r = await client.get(f"/api/v1/subjects/{s.id}")
        assert r.status_code == 200
        assert r.json()["code"] == s.code

    async def test_get_subject_not_found(self, client: AsyncClient) -> None:
        import uuid
        r = await client.get(f"/api/v1/subjects/{uuid.uuid4()}")
        assert r.status_code == 404


class TestEnrollment:
    async def test_enroll_success(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        token = await _register_and_token(client)
        r = await client.post(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        assert r.json()["subject_id"] == str(s.id)

    async def test_enroll_duplicate(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        token = await _register_and_token(client)
        await client.post(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = await client.post(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409

    async def test_enroll_requires_auth(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        r = await client.post(f"/api/v1/subjects/{s.id}/enroll")
        assert r.status_code == 401

    async def test_enroll_unknown_subject(self, client: AsyncClient) -> None:
        import uuid
        token = await _register_and_token(client)
        r = await client.post(
            f"/api/v1/subjects/{uuid.uuid4()}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    async def test_unenroll_success(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        token = await _register_and_token(client)
        await client.post(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = await client.delete(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204

    async def test_unenroll_not_enrolled(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        token = await _register_and_token(client)
        r = await client.delete(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404


class TestMySubjects:
    async def test_my_subjects_empty(self, client: AsyncClient, db: AsyncSession) -> None:
        await _seed_subjects(db)
        token = await _register_and_token(client)
        r = await client.get(
            "/api/v1/subjects/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    async def test_my_subjects_after_enroll(self, client: AsyncClient, db: AsyncSession) -> None:
        [sa, sb, *_] = await _seed_subjects(db)
        token = await _register_and_token(client)
        for s in [sa, sb]:
            await client.post(
                f"/api/v1/subjects/{s.id}/enroll",
                headers={"Authorization": f"Bearer {token}"},
            )
        r = await client.get(
            "/api/v1/subjects/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 2

    async def test_my_subjects_after_unenroll(self, client: AsyncClient, db: AsyncSession) -> None:
        [s, *_] = await _seed_subjects(db)
        token = await _register_and_token(client)
        await client.post(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.delete(
            f"/api/v1/subjects/{s.id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = await client.get(
            "/api/v1/subjects/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["total"] == 0

    async def test_my_subjects_requires_auth(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/subjects/me")
        assert r.status_code == 401
