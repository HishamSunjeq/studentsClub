import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
