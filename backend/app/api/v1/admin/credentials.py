"""Admin credential endpoints (Phase 2).

API keys are stored encrypted (Fernet) and **never** sent to the
frontend in plaintext — responses include only `key_last4`. Add /
rotate accept the plaintext key over HTTPS in the request body.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select

from app.api.deps import AdminUser, DBSession
from app.ai.credentials import (
    CredentialError,
    decrypt_api_key,
    encrypt_api_key,
)
from app.models.ai_credential import AICredential, CredentialProvider
from app.schemas.admin import (
    CredentialCreateRequest,
    CredentialListResponse,
    CredentialResponse,
    CredentialRotateRequest,
    CredentialTestResponse,
    CredentialUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=CredentialListResponse, operation_id="admin_credentials_list")
async def list_credentials(
    db: DBSession, _: AdminUser, provider: str | None = None
) -> CredentialListResponse:
    q = select(AICredential).order_by(AICredential.provider.asc(), AICredential.alias.asc())
    if provider:
        q = q.where(AICredential.provider == CredentialProvider(provider))
    rows = (await db.execute(q)).scalars().all()
    return CredentialListResponse(
        items=[CredentialResponse.model_validate(r) for r in rows]
    )


@router.post(
    "",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="admin_credentials_create",
)
async def create_credential(
    db: DBSession, admin: AdminUser, payload: CredentialCreateRequest
) -> CredentialResponse:
    existing = (
        await db.execute(select(AICredential).where(AICredential.alias == payload.alias))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Credential alias {payload.alias!r} already in use")

    try:
        ciphertext, last4 = encrypt_api_key(payload.api_key)
    except CredentialError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    row = AICredential(
        alias=payload.alias,
        provider=CredentialProvider(payload.provider),
        display_name=payload.display_name or payload.alias,
        key_encrypted=ciphertext,
        key_last4=last4,
        monthly_budget_usd=payload.monthly_budget_usd,
        created_by=admin.id,
    )
    db.add(row)
    await db.flush()
    return CredentialResponse.model_validate(row)


@router.patch(
    "/{credential_id}",
    response_model=CredentialResponse,
    operation_id="admin_credentials_update",
)
async def update_credential(
    db: DBSession,
    _: AdminUser,
    credential_id: uuid.UUID,
    payload: CredentialUpdateRequest,
) -> CredentialResponse:
    row = await _get_or_404(db, credential_id)
    if payload.display_name is not None:
        row.display_name = payload.display_name
    if payload.monthly_budget_usd is not None:
        row.monthly_budget_usd = payload.monthly_budget_usd
    if payload.is_active is not None:
        row.is_active = payload.is_active
    await db.flush()
    return CredentialResponse.model_validate(row)


@router.post(
    "/{credential_id}/rotate",
    response_model=CredentialResponse,
    operation_id="admin_credentials_rotate",
)
async def rotate_credential(
    db: DBSession,
    _: AdminUser,
    credential_id: uuid.UUID,
    payload: CredentialRotateRequest,
) -> CredentialResponse:
    row = await _get_or_404(db, credential_id)
    try:
        ciphertext, last4 = encrypt_api_key(payload.api_key)
    except CredentialError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    row.key_encrypted = ciphertext
    row.key_last4 = last4
    await db.flush()
    return CredentialResponse.model_validate(row)


@router.delete(
    "/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="admin_credentials_delete",
)
async def delete_credential(
    db: DBSession, _: AdminUser, credential_id: uuid.UUID
) -> None:
    row = await _get_or_404(db, credential_id)
    await db.delete(row)


@router.post(
    "/{credential_id}/test",
    response_model=CredentialTestResponse,
    operation_id="admin_credentials_test",
)
async def test_credential(
    db: DBSession, _: AdminUser, credential_id: uuid.UUID
) -> CredentialTestResponse:
    """Dry-run the credential against its provider with a 1-token call.
    Never returns the plaintext key in errors.
    """
    row = await _get_or_404(db, credential_id)
    try:
        key = decrypt_api_key(row.key_encrypted)
    except CredentialError as exc:
        return CredentialTestResponse(ok=False, detail=str(exc))

    start = time.monotonic()
    try:
        ok, detail = await _probe(row.provider.value, key)
    except Exception as exc:
        return CredentialTestResponse(
            ok=False,
            detail=f"{type(exc).__name__}: {exc}",
            latency_ms=int((time.monotonic() - start) * 1000),
        )

    return CredentialTestResponse(
        ok=ok,
        detail=detail,
        latency_ms=int((time.monotonic() - start) * 1000),
    )


async def _probe(provider: str, api_key: str) -> tuple[bool, str | None]:
    """Provider-specific 'is this key valid' check. Cheapest possible call."""
    if provider == "anthropic":
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key)
            # /v1/models is cheap and unmetered.
            await client.models.list(limit=1)
            return True, None
        except ImportError:
            return False, "anthropic SDK not installed"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {str(exc)[:200]}"

    if provider == "openai":
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            await client.models.list()
            return True, None
        except ImportError:
            return False, "openai SDK not installed"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {str(exc)[:200]}"

    # cohere / voyage / qdrant: skip live check, just confirm decryption worked.
    return True, f"Decryption succeeded; no live probe implemented for {provider}"


async def _get_or_404(db, credential_id: uuid.UUID) -> AICredential:
    row = (
        await db.execute(select(AICredential).where(AICredential.id == credential_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    return row
