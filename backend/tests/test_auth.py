import pytest
from httpx import AsyncClient


REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "password123",
    "full_name": "Alice Smith",
    "college": "Engineering",
    "academic_year": 2,
}


class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert r.status_code == 201
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        r = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert r.status_code == 409

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        payload = {**REGISTER_PAYLOAD, "email": "not-an-email"}
        r = await client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_short_password(self, client: AsyncClient) -> None:
        payload = {**REGISTER_PAYLOAD, "password": "short"}
        r = await client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_invalid_academic_year(self, client: AsyncClient) -> None:
        payload = {**REGISTER_PAYLOAD, "academic_year": 9}
        r = await client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": "wrongpassword"},
        )
        assert r.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert r.status_code == 401

    async def test_login_email_case_insensitive(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        r = await client.post(
            "/api/v1/auth/login",
            json={
                "email": REGISTER_PAYLOAD["email"].upper(),
                "password": REGISTER_PAYLOAD["password"],
            },
        )
        assert r.status_code == 200


class TestRefreshAndLogout:
    async def test_refresh_success(self, client: AsyncClient) -> None:
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        refresh_token = reg.json()["refresh_token"]

        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["refresh_token"] != refresh_token  # rotated

    async def test_refresh_revoked_on_reuse(self, client: AsyncClient) -> None:
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        old_token = reg.json()["refresh_token"]

        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_token})
        # reusing the rotated-away token must fail
        r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_token})
        assert r.status_code == 401

    async def test_logout_invalidates_refresh_token(self, client: AsyncClient) -> None:
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        refresh_token = reg.json()["refresh_token"]

        r = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert r.status_code == 204

        r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r2.status_code == 401


class TestUsersMe:
    async def test_get_me_success(self, client: AsyncClient) -> None:
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        access_token = reg.json()["access_token"]

        r = await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == REGISTER_PAYLOAD["email"]
        assert body["full_name"] == REGISTER_PAYLOAD["full_name"]
        assert body["role"] == "student"

    async def test_get_me_no_token(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/users/me")
        assert r.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient) -> None:
        r = await client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert r.status_code == 401


class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient) -> None:
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        access_token = reg.json()["access_token"]

        r = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": REGISTER_PAYLOAD["password"],
                "new_password": "newpassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r.status_code == 204

        # Old password should no longer work
        r2 = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
        )
        assert r2.status_code == 401

        # New password works
        r3 = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": "newpassword456"},
        )
        assert r3.status_code == 200

    async def test_change_password_wrong_current(self, client: AsyncClient) -> None:
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        access_token = reg.json()["access_token"]

        r = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongpassword", "new_password": "newpassword456"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r.status_code == 422
