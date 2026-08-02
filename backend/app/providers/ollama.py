"""Ollama LLM provider implementation with streaming support."""
import json
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from app.core.config import settings
from app.providers.base import BaseLLMProvider, ChatMessage, StreamChunk


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider via HTTP API."""

    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = model or settings.OLLAMA_MODEL
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
        )

    def _build_ollama_messages(self, messages: list[ChatMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completions from Ollama."""
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": self._build_ollama_messages(messages),
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with self._client.stream(
            "POST", "/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    message = data.get("message", {})
                    content = message.get("content", "")
                    is_done = data.get("done", False)
                    if content:
                        yield StreamChunk(
                            content=content,
                            is_done=is_done,
                            model=target_model,
                        )
                    if is_done:
                        yield StreamChunk(content="", is_done=True, model=target_model)
                        break
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Ollama stream line: {line}")
                    continue

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat request and return the full response."""
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": self._build_ollama_messages(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
