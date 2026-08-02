"""Anthropic Claude LLM provider implementation with streaming support."""
import json
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from app.core.config import settings
from app.providers.base import BaseLLMProvider, ChatMessage, StreamChunk

ANTHROPIC_API_URL = "https://api.anthropic.com/v1"
ANTHROPIC_DEFAULT_MODEL = "claude-3-5-haiku-20241022"
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider via Messages API."""

    provider_name: str = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.default_model = model or ANTHROPIC_DEFAULT_MODEL
        self._client = httpx.AsyncClient(
            base_url=ANTHROPIC_API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
        )

    def _split_messages(
        self, messages: list[ChatMessage]
    ) -> tuple[str, list[dict]]:
        """Separate system message from user/assistant messages."""
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})
        return system_content, chat_messages

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completions from Anthropic Claude."""
        if not self.api_key:
            raise ValueError("Anthropic API key is not configured.")

        target_model = model or self.default_model
        system_content, chat_messages = self._split_messages(messages)

        payload: dict = {
            "model": target_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
            "stream": True,
        }
        if system_content:
            payload["system"] = system_content

        async with self._client.stream(
            "POST", "/messages", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]" or not raw:
                    continue
                try:
                    data = json.loads(raw)
                    event_type = data.get("type", "")
                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        content = delta.get("text", "")
                        if content:
                            yield StreamChunk(
                                content=content,
                                is_done=False,
                                model=target_model,
                            )
                    elif event_type == "message_stop":
                        yield StreamChunk(
                            content="", is_done=True, model=target_model
                        )
                        break
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Anthropic stream line: {line}")
                    continue

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat request and return the full response."""
        if not self.api_key:
            raise ValueError("Anthropic API key is not configured.")

        target_model = model or self.default_model
        system_content, chat_messages = self._split_messages(messages)

        payload: dict = {
            "model": target_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_content:
            payload["system"] = system_content

        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        content_blocks = data.get("content", [])
        return "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )

    async def health_check(self) -> bool:
        """Check if Anthropic API is configured and reachable."""
        if not self.api_key:
            return False
        try:
            # Send a minimal request to verify API key validity
            response = await self._client.post(
                "/messages",
                json={
                    "model": self.default_model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
                timeout=10.0,
            )
            return response.status_code in (200, 400)  # 400 may be invalid content
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
