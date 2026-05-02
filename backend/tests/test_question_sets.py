import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import (
    Question,
    QuestionChoice,
    QuestionDifficulty,
    QuestionSet,
    QuestionSetStatus,
)
from app.models.subject import Subject
from app.models.upload import Upload, UploadStatus
from app.models.user import User

REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "password123",
    "full_name": "Owner",
    "college": "Engineering",
    "academic_year": 2,
}


async def _register_and_token(client: AsyncClient, email: str = "owner@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register", json={**REGISTER_PAYLOAD, "email": email}
    )
    return r.json()["access_token"]


async def _user_by_email(db: AsyncSession, email: str) -> User:
    from sqlalchemy import select
    return (await db.scalars(select(User).where(User.email == email))).one()


async def _seed_subject_and_upload(db: AsyncSession, user: User) -> tuple[Subject, Upload]:
    subject = Subject(
        name="Data Structures",
        code="CS201",
        college="Engineering",
        academic_year=2,
    )
    db.add(subject)
    await db.flush()

    upload = Upload(
        user_id=user.id,
        subject_id=subject.id,
        original_filename="notes.pdf",
        content_type="application/pdf",
        size_bytes=10_000,
        s3_key=f"uploads/{user.id}/{uuid.uuid4()}/notes.pdf",
        status=UploadStatus.finalized,
    )
    db.add(upload)
    await db.flush()
    return subject, upload


async def _seed_question_set(
    db: AsyncSession,
    user: User,
    upload: Upload,
    subject: Subject,
    *,
    status: QuestionSetStatus = QuestionSetStatus.draft,
    n_questions: int = 3,
) -> QuestionSet:
    qs = QuestionSet(
        upload_id=upload.id,
        subject_id=subject.id,
        created_by=user.id,
        title="Generated set",
        status=status,
        ai_model="mock",
        tokens_used=100,
    )
    db.add(qs)
    await db.flush()

    for q_pos in range(n_questions):
        q = Question(
            question_set_id=qs.id,
            text=f"Question {q_pos + 1}?",
            explanation="Because...",
            difficulty=QuestionDifficulty.medium,
            source_excerpt="excerpt",
            is_active=True,
            position=q_pos,
        )
        db.add(q)
        await db.flush()
        for c_pos in range(4):
            db.add(
                QuestionChoice(
                    question_id=q.id,
                    text=f"Choice {c_pos + 1}",
                    is_correct=(c_pos == 0),
                    position=c_pos,
                )
            )
    await db.flush()
    return qs


class TestListMyQuestionSets:
    async def test_empty(self, client: AsyncClient) -> None:
        token = await _register_and_token(client)
        r = await client.get(
            "/api/v1/question-sets/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    async def test_populated(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        await _seed_question_set(db, user, upload, subject)
        r = await client.get(
            "/api/v1/question-sets/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Generated set"

    async def test_filter_by_status(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        await _seed_question_set(db, user, upload, subject, status=QuestionSetStatus.draft)
        await _seed_question_set(db, user, upload, subject, status=QuestionSetStatus.published)
        r = await client.get(
            "/api/v1/question-sets/me?status=published",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["total"] == 1

    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/question-sets/me")
        assert r.status_code == 401


class TestGetQuestionSet:
    async def test_get_with_questions(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject, n_questions=2)
        r = await client.get(
            f"/api/v1/question-sets/{qs.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["questions"]) == 2
        assert len(body["questions"][0]["choices"]) == 4

    async def test_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_token(client)
        r = await client.get(
            f"/api/v1/question-sets/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    async def test_other_users_forbidden(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client, "owner@example.com")
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)

        other_token = await _register_and_token(client, "intruder@example.com")
        r = await client.get(
            f"/api/v1/question-sets/{qs.id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert r.status_code == 403


class TestUpdateTitle:
    async def test_success(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        r = await client.patch(
            f"/api/v1/question-sets/{qs.id}",
            json={"title": "Renamed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Renamed"

    async def test_blocked_when_published(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(
            db, user, upload, subject, status=QuestionSetStatus.published
        )
        r = await client.patch(
            f"/api/v1/question-sets/{qs.id}",
            json={"title": "Renamed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409


class TestPublish:
    async def test_success(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        r = await client.post(
            f"/api/v1/question-sets/{qs.id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    async def test_no_active_questions(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject, n_questions=0)
        r = await client.post(
            f"/api/v1/question-sets/{qs.id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409

    async def test_already_published(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(
            db, user, upload, subject, status=QuestionSetStatus.published
        )
        r = await client.post(
            f"/api/v1/question-sets/{qs.id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409


class TestReject:
    async def test_success(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        r = await client.post(
            f"/api/v1/question-sets/{qs.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"


class TestUpdateQuestion:
    async def _first_question(self, db: AsyncSession, qs_id: uuid.UUID) -> Question:
        from sqlalchemy import select
        return (
            await db.scalars(
                select(Question).where(Question.question_set_id == qs_id).order_by(Question.position)
            )
        ).first()

    async def test_update_text(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        q = await self._first_question(db, qs.id)
        r = await client.patch(
            f"/api/v1/questions/{q.id}",
            json={"text": "Updated?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["text"] == "Updated?"

    async def test_update_choices_replaces_all(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        q = await self._first_question(db, qs.id)
        r = await client.patch(
            f"/api/v1/questions/{q.id}",
            json={
                "choices": [
                    {"text": "A", "is_correct": False},
                    {"text": "B", "is_correct": True},
                    {"text": "C", "is_correct": False},
                    {"text": "D", "is_correct": False},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert [c["text"] for c in body["choices"]] == ["A", "B", "C", "D"]
        assert sum(1 for c in body["choices"] if c["is_correct"]) == 1

    async def test_update_choices_validates_count(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        q = await self._first_question(db, qs.id)
        r = await client.patch(
            f"/api/v1/questions/{q.id}",
            json={
                "choices": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": False},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    async def test_update_choices_validates_one_correct(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        q = await self._first_question(db, qs.id)
        r = await client.patch(
            f"/api/v1/questions/{q.id}",
            json={
                "choices": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": True},
                    {"text": "C", "is_correct": False},
                    {"text": "D", "is_correct": False},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    async def test_blocked_when_published(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(
            db, user, upload, subject, status=QuestionSetStatus.published
        )
        q = await self._first_question(db, qs.id)
        r = await client.patch(
            f"/api/v1/questions/{q.id}",
            json={"text": "Updated?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409

    async def test_deactivate(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "owner@example.com")
        subject, upload = await _seed_subject_and_upload(db, user)
        qs = await _seed_question_set(db, user, upload, subject)
        q = await self._first_question(db, qs.id)
        r = await client.delete(
            f"/api/v1/questions/{q.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204

        # Verify it's now is_active=False but still present
        r2 = await client.get(
            f"/api/v1/question-sets/{qs.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        deactivated = next(qq for qq in r2.json()["questions"] if qq["id"] == str(q.id))
        assert deactivated["is_active"] is False
