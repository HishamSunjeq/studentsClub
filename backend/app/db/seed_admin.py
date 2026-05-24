"""Seed a default admin user on first boot.

Idempotent: if any active user with `role=admin` already exists, this is a no-op.
Otherwise creates one from `settings.default_admin_*` and logs the credentials
once so the operator can sign in.

Set `DEFAULT_ADMIN_SEED_ENABLED=0` to skip entirely.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole

log = structlog.get_logger()


async def ensure_default_admin() -> None:
    if not settings.default_admin_seed_enabled:
        return

    async with AsyncSessionLocal() as db:
        existing_admin = await db.scalar(
            select(User.id).where(User.role == UserRole.admin, User.is_active.is_(True))
        )
        if existing_admin is not None:
            return

        email = settings.default_admin_email.strip().lower()
        existing_by_email = await db.scalar(select(User).where(User.email == email))
        if existing_by_email is not None:
            # Email is taken by a non-admin — promote rather than crash.
            existing_by_email.role = UserRole.admin
            await db.commit()
            log.info("default_admin_promoted", email=email)
            return

        admin = User(
            email=email,
            password_hash=hash_password(settings.default_admin_password),
            full_name=settings.default_admin_name,
            college=settings.default_admin_college,
            academic_year=settings.default_admin_year,
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.commit()

        # Log loudly so the operator notices on first boot. The password is the
        # value from settings — if it's still the dev default, that's already
        # public knowledge; if the operator overrode it via env, they already
        # know it.
        log.warning(
            "default_admin_created",
            email=email,
            password=settings.default_admin_password,
            note="Sign in with these credentials, then change the password.",
        )
