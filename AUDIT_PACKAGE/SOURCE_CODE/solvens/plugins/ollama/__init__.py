"""Ollama provider plugin for SOLVENS CORE - Local LLM support."""

from __future__ import annotations

from typing import Any, AsyncIterator
import json

import httpx

from solvens.core.types import Message, Model, ModelCapability, ProviderType, Response, TokenUsage
from solvens.providers.base import ProviderClient


class OllamaClient(ProviderClient):
    """Ollama API client for local LLM inference."""
    
    DEFAULT_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    
    def __init__(self, base_url: str | None = None, timeout: float = 120.0, **kwargs: Any):
        self.base_url = base_url or self.DEFAULT_URL
        self.timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    @property
    def provider_name(self) -> str:
        return "Ollama"
    
    @property
    def supports_function_calling(self) -> bool:
        return False
    
    def _convert_messages(self, messages: list[Message]) -> str:
        """Convert messages to Ollama format."""
        result = []
        for msg in messages:
            result.append(f"{msg.role.value}: {msg.content}")
        return "\n".join(result)

    async def chat(self, messages: list[Message], model: str | None = None, **options: Any) -> Response:
        model = model or self.DEFAULT_MODEL
        prompt = self._convert_messages(messages)
        payload = {"model": model, "prompt": prompt, "stream": False, **options}
        
        response = await self._client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return Response(
            content=data.get("response", ""),
            model=model,
            metadata={"done": data.get("done"), "context": data.get("context")},
        )

    async def chat_stream(self, messages: list[Message], model: str | None = None, **options: Any) -> AsyncIterator[str]:
        model = model or self.DEFAULT_MODEL
        prompt = self._convert_messages(messages)
        payload = {"model": model, "prompt": prompt, "stream": True, **options}
        
        async with self._client.stream("POST", "/api/generate", json=payload) as stream:
            stream.raise_for_status()
            async for line in stream.aiter_lines():
                if line.strip():
                    chunk = json.loads(line)  # Ollama returns one JSON object per line
                    if not isinstance(chunk, dict):
                        raise ValueError("Invalid Ollama stream chunk: expected JSON object")
                    if "response" in chunk:
                        yield chunk["response"]

    async def embeddings(self, texts: list[str], model: str | None = None, **options: Any) -> list[list[float]]:
        model = model or "nomic-embed-text"
        results = []
        for text in texts:
            payload = {"model": model, "prompt": text, **options}
            response = await self._client.post("/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            results.append(data.get("embedding", []))
        return results

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def get_available_models(self) -> list[Model]:
        return [
            Model(id="llama3.2", name="Llama 3.2", provider=ProviderType.OLLAMA,
                  capabilities=[ModelCapability.CHAT, ModelCapability.STREAMING], max_tokens=8192),
            Model(id="llama3.2-vision", name="Llama 3.2 Vision", provider=ProviderType.OLLAMA,
                  capabilities=[ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.STREAMING], max_tokens=8192),
            Model(id="codellama", name="Code Llama", provider=ProviderType.OLLAMA,
                  capabilities=[ModelCapability.CHAT, ModelCapability.STREAMING], max_tokens=16384),
            Model(id="nomic-embed-text", name="Nomic Embed Text", provider=ProviderType.OLLAMA,
                  capabilities=[ModelCapability.EMBEDDINGS]),
        ]
