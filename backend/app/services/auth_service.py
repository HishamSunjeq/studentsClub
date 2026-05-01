from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth_tokens import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse


async def register(
    *,
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    college: str,
    academic_year: int,
) -> tuple[User, TokenResponse]:
    existing = await db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        raise ConflictError("An account with that email already exists")

    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        college=college,
        academic_year=academic_year,
    )
    db.add(user)
    await db.flush()  # populate user.id without committing

    tokens = await _issue_tokens(db=db, user=user)
    await db.commit()
    await db.refresh(user)
    return user, tokens


async def login(
    *,
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, TokenResponse]:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    tokens = await _issue_tokens(db=db, user=user)
    await db.commit()
    return user, tokens


async def refresh(*, db: AsyncSession, raw_token: str) -> TokenResponse:
    token_hash = hash_token(raw_token)
    record = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if not record or not record.is_valid:
        raise UnauthorizedError("Invalid or expired refresh token")

    # Rotate: revoke the old token, issue a new pair
    record.revoked_at = datetime.now(UTC)

    user = await db.get(User, record.user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or disabled")

    tokens = await _issue_tokens(db=db, user=user)
    await db.commit()
    return tokens


async def logout(*, db: AsyncSession, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    record = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        await db.commit()


async def change_password(
    *,
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    # Revoke all existing refresh tokens (force re-login everywhere)
    existing = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for token in existing:
        token.revoked_at = now
    await db.commit()


async def _issue_tokens(*, db: AsyncSession, user: User) -> TokenResponse:
    raw = generate_opaque_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=expires_at,
        created_at=datetime.now(UTC),
    )
    db.add(rt)

    access_token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw,
        expires_in=settings.access_token_ttl_minutes * 60,
    )
