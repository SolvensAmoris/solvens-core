"""Anthropic provider plugin for SOLVENS CORE - Claude models."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from solvens.core.types import Message, Model, ModelCapability, ProviderType, Response, TokenUsage
from solvens.providers.base import ProviderClient


class AnthropicClient(ProviderClient):
    """Anthropic API client for Claude models."""
    
    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    API_VERSION = "2023-06-01"
    
    def __init__(self, api_key: str, base_url: str | None = None, timeout: float = 60.0, **kwargs: Any):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "anthropic-version": self.API_VERSION,
                "Content-Type": "application/json",
            },
        )
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    @property
    def provider_name(self) -> str:
        return "Anthropic"
    
    @property
    def supports_vision(self) -> bool:
        return True
    
    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert SOLVENS messages to Anthropic format."""
        result = []
        for msg in messages:
            if msg.role.value == "system":
                continue  # System messages handled separately
            item = {"role": msg.role.value if msg.role.value != "assistant" else "assistant", "content": msg.content}
            result.append(item)
        return result

    async def chat(self, messages: list[Message], model: str | None = None, **options: Any) -> Response:
        model = model or self.DEFAULT_MODEL
        system = next((m.content for m in messages if m.role.value == "system"), None)
        conversation = self._convert_messages(messages)
        
        payload = {
            "model": model,
            "messages": conversation,
            "max_tokens": options.get("max_tokens", 1024),
            **({"system": system} if system else {}),
            **{k: v for k, v in options.items() if k not in ["max_tokens"]},
        }
        
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        
        content = data["content"][0]["text"] if data.get("content") else ""
        usage = data.get("usage", {})
        
        return Response(
            content=content,
            model=model,
            usage=TokenUsage(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            ),
            metadata={"id": data.get("id"), "model": data.get("model")},
        )

    async def chat_stream(self, messages: list[Message], model: str | None = None, **options: Any) -> AsyncIterator[str]:
        model = model or self.DEFAULT_MODEL
        system = next((m.content for m in messages if m.role.value == "system"), None)
        conversation = self._convert_messages(messages)
        
        payload = {
            "model": model,
            "messages": conversation,
            "max_tokens": options.get("max_tokens", 1024),
            "stream": True,
            **({"system": system} if system else {}),
            **{k: v for k, v in options.items() if k not in ["max_tokens"]},
        }
        
        async with self._client.stream("POST", "/messages", json=payload) as stream:
            stream.raise_for_status()
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        chunk = json.loads(data_str)
                        if chunk.get("type") == "content_block_delta":
                            if "text" in chunk.get("delta", {}):
                                yield chunk["delta"]["text"]

    async def embeddings(self, texts: list[str], model: str | None = None, **options: Any) -> list[list[float]]:
        raise NotImplementedError("Anthropic does not provide a standalone embeddings API")

    async def vision(self, image: str | bytes, prompt: str, model: str | None = None, **options: Any) -> Response:
        model = model or "claude-3-5-sonnet-20241022"
        
        # Handle image data
        if isinstance(image, str):
            if image.startswith("data:"):
                media_type, b64_data = image.split(",", 1)
                media_type = media_type.split(":")[1].split(";")[0]
            else:
                media_type = "image/png"
                b64_data = image
        else:
            import base64
            media_type = "image/png"
            b64_data = base64.b64encode(image).decode()
        
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_data}},
                    {"type": "text", "text": prompt},
                ],
            }],
            "max_tokens": options.get("max_tokens", 1024),
        }
        
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return Response(
            content=data["content"][0]["text"],
            model=model,
            metadata={"id": data.get("id")},
        )

    async def health_check(self) -> bool:
        try:
            payload = {"model": self.DEFAULT_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
            response = await self._client.post("/messages", json=payload)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    def get_available_models(self) -> list[Model]:
        return [
            Model(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", provider=ProviderType.ANTHROPIC,
                  capabilities=[ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.STREAMING], max_tokens=8192),
            Model(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku", provider=ProviderType.ANTHROPIC,
                  capabilities=[ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.STREAMING], max_tokens=8192),
            Model(id="claude-3-opus-20240229", name="Claude 3 Opus", provider=ProviderType.ANTHROPIC,
                  capabilities=[ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.STREAMING], max_tokens=4096),
            Model(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet", provider=ProviderType.ANTHROPIC,
                  capabilities=[ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.STREAMING], max_tokens=4096),
        ]
