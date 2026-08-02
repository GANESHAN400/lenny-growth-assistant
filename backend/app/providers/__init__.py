"""Provider factory and exports."""
from app.core.config import settings
from app.providers.anthropic import AnthropicProvider
from app.providers.base import BaseLLMProvider, ChatMessage, StreamChunk
from app.providers.ollama import OllamaProvider

__all__ = [
    "AnthropicProvider",
    "BaseLLMProvider",
    "ChatMessage",
    "OllamaProvider",
    "StreamChunk",
    "get_provider",
]


def get_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Factory function to get the appropriate LLM provider."""
    name = provider_name or settings.DEFAULT_PROVIDER
    if name == "anthropic":
        return AnthropicProvider()
    return OllamaProvider()
