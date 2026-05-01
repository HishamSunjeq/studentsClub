from app.ai.base import AIProvider
from app.core.config import settings


def get_provider(name: str | None = None) -> AIProvider:
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
