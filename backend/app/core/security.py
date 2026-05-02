import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def _bcrypt_input(password: str) -> bytes:
    # bcrypt has a hard 72-byte ceiling. Truncate explicitly so behavior is
    # stable across bcrypt versions (older silently truncated, 4.x raises).
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_input(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_ttl_minutes)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict[str, object]:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def generate_opaque_token() -> str:
    """Return a cryptographically random URL-safe token (not stored — hash it first)."""
    return secrets.token_urlsafe(64)


def hash_token(raw: str) -> str:
    """SHA-256 hash of a raw opaque token — safe to store in the DB."""
    return hashlib.sha256(raw.encode()).hexdigest()
