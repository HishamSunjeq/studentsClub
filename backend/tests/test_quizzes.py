import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
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
    "email": "quizzer@example.com",
    "password": "password123",
    "full_name": "Quiz Taker",
    "college": "Engineering",
    "academic_year": 2,
}


async def _register_and_token(client: AsyncClient, email: str = "quizzer@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register", json={**REGISTER_PAYLOAD, "email": email}
    )
    return r.json()["access_token"]


async def _user_by_email(db: AsyncSession, email: str) -> User:
    return (await db.scalars(select(User).where(User.email == email))).one()


async def _seed_published_set(
    db: AsyncSession, user: User, *, n_questions: int = 5
) -> tuple[Subject, list[Question]]:
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
        status=UploadStatus.ready,
    )
    db.add(upload)
    await db.flush()

    qs = QuestionSet(
        upload_id=upload.id,
        subject_id=subject.id,
        created_by=user.id,
        title="DS quiz",
        status=QuestionSetStatus.published,
        ai_model="mock",
        tokens_used=0,
    )
    db.add(qs)
    await db.flush()

    questions: list[Question] = []
    for q_pos in range(n_questions):
        q = Question(
            question_set_id=qs.id,
            text=f"Question {q_pos + 1}?",
            explanation=f"Reason {q_pos + 1}",
            difficulty=QuestionDifficulty.medium,
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
        questions.append(q)
    await db.flush()
    return subject, questions


async def _correct_choice(db: AsyncSession, question_id: uuid.UUID) -> QuestionChoice:
    return (
        await db.scalars(
            select(QuestionChoice).where(
                QuestionChoice.question_id == question_id,
                QuestionChoice.is_correct.is_(True),
            )
        )
    ).one()


async def _wrong_choice(db: AsyncSession, question_id: uuid.UUID) -> QuestionChoice:
    return (
        await db.scalars(
            select(QuestionChoice).where(
                QuestionChoice.question_id == question_id,
                QuestionChoice.is_correct.is_(False),
            )
        )
    ).first()


class TestStartQuiz:
    async def test_success(self, client: AsyncClient, db: AsyncSession) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=5)
        r = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject.id), "count": 3},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["total_questions"] == 3
        assert len(body["questions"]) == 3
        # Server must NOT leak is_correct
        for q in body["questions"]:
            for c in q["choices"]:
                assert "is_correct" not in c

    async def test_count_capped_to_available(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=2)
        r = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject.id), "count": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        assert r.json()["total_questions"] == 2

    async def test_no_published_questions(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        # Subject with no question sets
        subject = Subject(
            name="Empty", code="EMPTY", college="Engineering", academic_year=1
        )
        db.add(subject)
        await db.flush()
        r = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject.id), "count": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(uuid.uuid4()), "count": 5},
        )
        assert r.status_code == 401


class TestSubmitAnswer:
    async def _start(self, client: AsyncClient, token: str, subject_id: uuid.UUID, count: int = 3):
        r = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject_id), "count": count},
            headers={"Authorization": f"Bearer {token}"},
        )
        return r.json()

    async def test_correct_answer_increments_score(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=3)
        session = await self._start(client, token, subject.id)

        first_q = session["questions"][0]
        correct = await _correct_choice(db, uuid.UUID(first_q["id"]))

        r = await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(correct.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["is_correct"] is True
        assert body["score"] == 1
        assert body["correct_choice_id"] == str(correct.id)

    async def test_wrong_answer_does_not_increment(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=3)
        session = await self._start(client, token, subject.id)

        first_q = session["questions"][0]
        wrong = await _wrong_choice(db, uuid.UUID(first_q["id"]))

        r = await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(wrong.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["is_correct"] is False
        assert body["score"] == 0

    async def test_duplicate_answer_rejected(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=3)
        session = await self._start(client, token, subject.id)

        first_q = session["questions"][0]
        correct = await _correct_choice(db, uuid.UUID(first_q["id"]))

        await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(correct.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        r2 = await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(correct.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 409

    async def test_other_user_cannot_answer(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=2)
        session = await self._start(client, token, subject.id)

        intruder_token = await _register_and_token(client, "intruder@example.com")
        first_q = session["questions"][0]
        correct = await _correct_choice(db, uuid.UUID(first_q["id"]))

        r = await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(correct.id)},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
        assert r.status_code == 403


class TestCompleteAndResume:
    async def test_complete_locks_session(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=2)

        r = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject.id), "count": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        session = r.json()

        first_q = session["questions"][0]
        correct = await _correct_choice(db, uuid.UUID(first_q["id"]))
        await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(correct.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        complete = await client.post(
            f"/api/v1/quizzes/{session['id']}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

        # Subsequent answers are rejected
        second_q = session["questions"][1]
        second_correct = await _correct_choice(db, uuid.UUID(second_q["id"]))
        r2 = await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": second_q["id"], "choice_id": str(second_correct.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 409

    async def test_resume_returns_picks_and_answered(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=3)

        start = await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject.id), "count": 3},
            headers={"Authorization": f"Bearer {token}"},
        )
        session = start.json()
        original_q_ids = [q["id"] for q in session["questions"]]

        # Answer one question
        first_q = session["questions"][0]
        correct = await _correct_choice(db, uuid.UUID(first_q["id"]))
        await client.post(
            f"/api/v1/quizzes/{session['id']}/answer",
            json={"question_id": first_q["id"], "choice_id": str(correct.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Resume
        resume = await client.get(
            f"/api/v1/quizzes/{session['id']}/questions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resume.status_code == 200
        body = resume.json()
        # Same question ids in same order
        assert [q["id"] for q in body["questions"]] == original_q_ids
        assert body["answered_question_ids"] == [first_q["id"]]


class TestListMyQuizzes:
    async def test_lists_own_sessions(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        token = await _register_and_token(client)
        user = await _user_by_email(db, "quizzer@example.com")
        subject, _ = await _seed_published_set(db, user, n_questions=2)
        await client.post(
            "/api/v1/quizzes",
            json={"subject_id": str(subject.id), "count": 2},
            headers={"Authorization": f"Bearer {token}"},
        )

        r = await client.get(
            "/api/v1/quizzes/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1
