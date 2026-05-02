import os
import re
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — registers all ORM models with Base.metadata
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base


def _resolve_test_database_url() -> str:
    """Allow override via TEST_DATABASE_URL; otherwise reuse the app's
    DATABASE_URL with a `_test` suffix. This lets tests run both inside
    Docker (postgres host) and on a developer machine (localhost)."""
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    base = settings.database_url
    return re.sub(r"(/[^/?]+)(\?|$)", r"\1_test\2", base, count=1)


TEST_DATABASE_URL = _resolve_test_database_url()


@pytest.fixture(scope="session")
def _schema_setup() -> None:
    """One-shot schema bootstrap. Uses a sync psycopg connection via a temp
    async engine so we avoid binding pool connections to a session-scoped
    event loop (which breaks under pytest-asyncio function-scoped loops)."""
    import asyncio

    async def _setup() -> None:
        eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await eng.dispose()

    asyncio.run(_setup())


@pytest.fixture
async def engine(_schema_setup: None):
    """Per-test engine using NullPool so every connection is brand-new and
    bound to the current event loop. NullPool trades connection reuse for
    correctness — fine for tests, never for prod."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Each test gets a session that survives app-code commit() calls.
    Pattern: outer transaction on a connection + auto-restarting SAVEPOINT;
    the savepoint listener uses the sync connection so the event handler
    (which is sync) doesn't try to await."""
    async with engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        session = AsyncSession(bind=conn, expire_on_commit=False, autoflush=False)

        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sess, trans):  # type: ignore[no-untyped-def]
            if conn.closed:
                return
            if not conn.in_nested_transaction():
                conn.sync_connection.begin_nested()

        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
