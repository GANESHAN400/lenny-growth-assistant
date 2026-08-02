"""Abstract base interface for LLM providers."""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class StreamChunk:
    content: str
    is_done: bool = False
    model: str = ""


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    provider_name: str = ""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request and return the full response."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and reachable."""
        ...
