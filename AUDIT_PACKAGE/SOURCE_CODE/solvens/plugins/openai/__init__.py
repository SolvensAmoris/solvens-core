"""OpenAI provider plugin for SOLVENS CORE."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from solvens.core.types import Message, Model, ModelCapability, ProviderType, Response, TokenUsage
from solvens.providers.base import ProviderClient


class OpenAIClient(ProviderClient):
    """OpenAI API client."""
    
    BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4"
    
    def __init__(self, api_key: str, base_url: str | None = None, timeout: float = 60.0, **kwargs: Any):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    @property
    def supports_function_calling(self) -> bool:
        return True
    
    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]

    async def chat(self, messages: list[Message], model: str | None = None, **options: Any) -> Response:
        model = model or self.DEFAULT_MODEL
        payload = {"model": model, "messages": self._convert_messages(messages), **options}
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return Response(
            content=choice["message"]["content"],
            model=model,
            usage=TokenUsage(prompt_tokens=usage.get("prompt_tokens", 0),
                           completion_tokens=usage.get("completion_tokens", 0),
                           total_tokens=usage.get("total_tokens", 0)),
            finish_reason=choice.get("finish_reason"),
        )

    async def chat_stream(self, messages: list[Message], model: str | None = None, **options: Any) -> AsyncIterator[str]:
        model = model or self.DEFAULT_MODEL
        payload = {"model": model, "messages": self._convert_messages(messages), "stream": True, **options}
        async with self._client.stream("POST", "/chat/completions", json=payload) as stream:
            stream.raise_for_status()
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() != "[DONE]":
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        if content := delta.get("content"):
                            yield content

    async def embeddings(self, texts: list[str], model: str | None = None, **options: Any) -> list[list[float]]:
        model = model or "text-embedding-3-small"
        payload = {"model": model, "input": texts, **options}
        response = await self._client.post("/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    def get_available_models(self) -> list[Model]:
        return [
            Model(id="gpt-4-turbo", name="GPT-4 Turbo", provider=ProviderType.OPENAI,
                  capabilities=[ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING], max_tokens=128000),
            Model(id="gpt-4", name="GPT-4", provider=ProviderType.OPENAI,
                  capabilities=[ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING], max_tokens=8192),
            Model(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", provider=ProviderType.OPENAI,
                  capabilities=[ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING], max_tokens=16385),
            Model(id="text-embedding-3-small", name="Embedding 3 Small", provider=ProviderType.OPENAI,
                  capabilities=[ModelCapability.EMBEDDINGS]),
        ]
