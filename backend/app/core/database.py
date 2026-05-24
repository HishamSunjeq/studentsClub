import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Celery runs each task in its own short-lived event loop (`asyncio.run`).
# A pooled connection checked in under one loop and reused under the next
# raises "Event loop is closed" when asyncpg tears it down. NullPool opens
# and fully closes a connection within the same task loop, so nothing
# survives across loops. The API (single long-lived loop) keeps QueuePool.
_WORKER_MODE = os.getenv("WORKER_MODE") == "1"

if _WORKER_MODE:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
