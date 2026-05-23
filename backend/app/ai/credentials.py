"""Provider credential storage + resolution (Phase 2).

Keys are encrypted at rest with Fernet symmetric encryption. The master
key lives in `settings.ai_credential_key` (32-byte url-safe base64).
Plaintext keys never leave the backend; the API responds with only
`key_last4`.

Resolution priority for a provider call:
    explicit alias arg
        -> alias on the active generation profile
        -> any global default credential for this provider
        -> `.env` fallback (back-compat — anthropic_api_key / openai_api_key)

The fallback is what lets the old single-key dev setup keep working.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_credential import AICredential, CredentialProvider

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Raised when a credential cannot be resolved or decrypted."""


@dataclass
class ResolvedCredential:
    alias: str | None
    provider: str
    api_key: str
    credential_id: uuid.UUID | None
    is_env_fallback: bool


def _fernet() -> Fernet:
    key = settings.ai_credential_key
    if not key:
        raise CredentialError(
            "AI_CREDENTIAL_KEY is not set; cannot encrypt/decrypt provider credentials. "
            "Set a 32-byte url-safe base64 key in .env to enable the credential store."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise CredentialError(f"AI_CREDENTIAL_KEY is not a valid Fernet key: {exc}") from exc


def encrypt_api_key(plaintext: str) -> tuple[bytes, str]:
    """Returns (ciphertext_bytes, last4_string)."""
    if not plaintext or len(plaintext) < 4:
        raise CredentialError("API key looks too short to be valid")
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token, plaintext[-4:]


def decrypt_api_key(ciphertext: bytes) -> str:
    try:
        return _fernet().decrypt(bytes(ciphertext)).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialError(
            "Stored credential could not be decrypted — has AI_CREDENTIAL_KEY rotated?"
        ) from exc


def generate_master_key() -> str:
    """Helper for ops: returns a fresh Fernet key as a url-safe base64 string."""
    return Fernet.generate_key().decode("utf-8")


# ---------- resolution ------------------------------------------------------


async def resolve(
    db: AsyncSession,
    *,
    provider: str,
    alias: str | None = None,
) -> ResolvedCredential:
    """Resolve a credential by alias (explicit), falling back to the global default
    for the provider, and finally to the `.env` legacy key.

    Never logs or returns the plaintext key in errors.
    """
    if alias:
        cred = (
            await db.execute(
                select(AICredential).where(
                    AICredential.alias == alias,
                    AICredential.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if cred is None:
            raise CredentialError(
                f"Credential alias {alias!r} not found or inactive."
            )
        if cred.provider.value != provider:
            raise CredentialError(
                f"Credential alias {alias!r} is for {cred.provider.value!r}, not {provider!r}."
            )
        return _from_row(cred)

    # No alias: try the first active credential for this provider (deterministic by alias).
    cred = (
        await db.execute(
            select(AICredential)
            .where(
                AICredential.provider == CredentialProvider(provider),
                AICredential.is_active.is_(True),
            )
            .order_by(AICredential.alias.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if cred is not None:
        return _from_row(cred)

    # Last resort: env fallback. Keeps the legacy dev setup working.
    env_key = _env_key_for(provider)
    if env_key:
        return ResolvedCredential(
            alias=None,
            provider=provider,
            api_key=env_key,
            credential_id=None,
            is_env_fallback=True,
        )

    raise CredentialError(
        f"No credential available for provider {provider!r}: no DB credential and no env fallback."
    )


def _from_row(cred: AICredential) -> ResolvedCredential:
    return ResolvedCredential(
        alias=cred.alias,
        provider=cred.provider.value,
        api_key=decrypt_api_key(cred.key_encrypted),
        credential_id=cred.id,
        is_env_fallback=False,
    )


def _env_key_for(provider: str) -> str | None:
    if provider == "anthropic":
        return settings.anthropic_api_key or None
    if provider == "openai":
        return settings.openai_api_key or None
    return None


async def mark_used(db: AsyncSession, credential_id: uuid.UUID) -> None:
    """Bump last_used_at — best-effort, swallows errors."""
    try:
        await db.execute(
            update(AICredential)
            .where(AICredential.id == credential_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
    except Exception:
        logger.exception("Failed to update last_used_at for credential %s", credential_id)
