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
from app.models.auth_tokens import PasswordResetToken, RefreshToken
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


async def forgot_password(*, db: AsyncSession, email: str) -> None:
    """Create a password-reset token and send it by email.
    Always returns silently (even if email not found) to prevent user enumeration."""
    import structlog
    log = structlog.get_logger()

    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return  # silent — don't reveal whether the address exists

    # Invalidate any existing unused tokens for this user
    existing = await db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for t in existing:
        t.used_at = now  # mark as consumed so they can't be used

    raw = generate_opaque_token()
    expires_at = now + timedelta(minutes=settings.password_reset_token_ttl_minutes)
    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=expires_at,
        created_at=now,
    )
    db.add(prt)
    await db.commit()

    reset_url = f"{settings.frontend_url}/reset-password?token={raw}"
    _send_reset_email(to=user.email, name=user.full_name, reset_url=reset_url)
    log.info("password_reset_requested", user_id=str(user.id))


async def reset_password(*, db: AsyncSession, raw_token: str, new_password: str) -> None:
    token_hash = hash_token(raw_token)
    record = await db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    now = datetime.now(UTC)
    if (
        record is None
        or record.used_at is not None
        or record.expires_at.replace(tzinfo=UTC) < now
    ):
        raise ValidationError("This reset link is invalid or has expired")

    user = await db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise ValidationError("This reset link is invalid or has expired")

    user.password_hash = hash_password(new_password)
    record.used_at = now

    # Revoke all refresh tokens (force re-login on all devices)
    existing_rt = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    for rt in existing_rt:
        rt.revoked_at = now

    await db.commit()


def _send_reset_email(*, to: str, name: str, reset_url: str) -> None:
    """Send the reset email via SMTP, or log to console if SMTP is not configured."""
    import smtplib
    import structlog
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    log = structlog.get_logger()

    if not settings.smtp_host:
        log.info("password_reset_link (no SMTP configured)", to=to, url=reset_url)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your StudentsClub password"
    msg["From"] = settings.smtp_from
    msg["To"] = to

    text_body = (
        f"Hi {name},\n\n"
        f"Click the link below to reset your password (expires in "
        f"{settings.password_reset_token_ttl_minutes} minutes):\n\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— StudentsClub"
    )
    html_body = f"""
    <p>Hi {name},</p>
    <p>Click the button below to reset your password. This link expires in
    {settings.password_reset_token_ttl_minutes} minutes.</p>
    <p><a href="{reset_url}" style="background:#4f46e5;color:#fff;padding:10px 20px;
    border-radius:6px;text-decoration:none;display:inline-block;">Reset password</a></p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    <p>— StudentsClub</p>
    """
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.sendmail(settings.smtp_from, to, msg.as_string())
        log.info("password_reset_email_sent", to=to)
    except Exception as exc:
        log.error("password_reset_email_failed", to=to, error=str(exc))

