"""Provider factory.

Phase 2: accepts an optional `credential_alias` that's resolved against
the `ai_credentials` table, and pulls the active extraction prompt from
the registry. Both have safe fallbacks (env vars + hardcoded prompt) so
the legacy synchronous `get_provider()` keeps working.
"""

from __future__ import annotations

from app.ai.base import AIProvider
from app.core.config import settings


def get_provider(name: str | None = None) -> AIProvider:
    """Synchronous, env-driven factory. Used by tests and legacy code.

    For DB-resolved credentials use `get_provider_async(...)`.
    """
    provider_name = name or settings.ai_provider

    if provider_name == "anthropic":
        from app.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if provider_name == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if provider_name == "mock":
        from app.ai.providers.mock_provider import MockProvider
        return MockProvider()

    raise ValueError(f"Unknown AI provider: {provider_name!r}")


async def get_provider_async(
    name: str | None = None,
    *,
    credential_alias: str | None = None,
    model: str | None = None,
    prompt_name: str = "extraction.system",
) -> AIProvider:
    """DB-aware factory. Resolves credential + model + prompt from the
    control plane (Phase 2). Falls back to env / hardcoded prompt when
    DB lookups fail, so callers don't need to special-case dev setups.
    """
    provider_name = name or settings.ai_provider

    if provider_name == "mock":
        from app.ai.providers.mock_provider import MockProvider
        return MockProvider()

    # Resolve prompt (best effort — falls back to hardcoded constant).
    system_prompt: str | None = None
    try:
        from app.ai.prompts_registry import get_active_prompt

        record = await get_active_prompt(prompt_name)
        system_prompt = record.content
    except Exception:
        system_prompt = None

    # Resolve credential.
    api_key: str | None = None
    try:
        from app.ai.credentials import resolve as resolve_credential
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            cred = await resolve_credential(db, provider=provider_name, alias=credential_alias)
            api_key = cred.api_key
    except Exception:
        api_key = None  # provider __init__ will fall back to env

    if provider_name == "anthropic":
        from app.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model=model, system_prompt=system_prompt)
    if provider_name == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model, system_prompt=system_prompt)

    raise ValueError(f"Unknown AI provider: {provider_name!r}")
