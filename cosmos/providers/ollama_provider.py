"""
Ollama Provider Implementation

Implements BaseProvider interface for Ollama local models.
FREE: No API costs for local inference.
"""

import os
from typing import Optional, AsyncIterator
from dataclasses import dataclass

from .base import (
    BaseProvider,
    ProviderType,
    Message,
    CompletionResult,
    EmbeddingResult,
    StreamingChunk,
    registry,
)


@dataclass
class OllamaConfig:
    """Ollama configuration."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    
    @classmethod
    def from_env(cls) -> "OllamaConfig":
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3"),
        )


class OllamaProvider(BaseProvider):
    """
    Ollama provider implementing BaseProvider interface.
    
    Supports local models: llama3, mixtral, codellama, etc.
    FREE: Zero API costs for local inference.
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig.from_env()
        self._client = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    @property
    def default_model(self) -> str:
        return self.config.model
    
    @property
    def supported_models(self) -> list[str]:
        return [
            "llama3",
            "llama3.1",
            "llama3.2",
            "mixtral",
            "mistral",
            "codellama",
            "phi3",
            "gemma2",
            "qwen2",
        ]
    
    def _get_client(self):
        """Lazy initialization of HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=120.0,
            )
        return self._client
    
    async def complete(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResult:
        """Send completion request to Ollama."""
        client = self._get_client()
        model = model or self.default_model
        
        # Convert messages to Ollama format
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return CompletionResult(
            content=data.get("response", ""),
            model=model,
            provider=self.provider_type.value,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            finish_reason=data.get("done_reason", "stop"),
            raw_response=data,
        )
    
    async def complete_stream(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """Send streaming completion request to Ollama."""
        client = self._get_client()
        model = model or self.default_model
        
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                
                import json
                try:
                    chunk = json.loads(line)
                except:
                    continue
                
                content = chunk.get("response", "")
                
                yield StreamingChunk(
                    content=content,
                    delta=content,
                    done=chunk.get("done", False),
                )
                
                if chunk.get("done"):
                    break
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResult:
        """Get embeddings from Ollama."""
        client = self._get_client()
        model = model or "nomic-embed-text"
        
        payload = {
            "model": model,
            "prompt": text,
        }
        
        response = await client.post("/api/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return EmbeddingResult(
            embedding=data.get("embedding", []),
            model=model,
            provider=self.provider_type.value,
            tokens=0,  # Ollama doesn't provide token counts
        )
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except:
            return False
    
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Ollama is FREE for local inference.
        Zero API costs.
        """
        return 0.0
    
    def supports_function_calling(self) -> bool:
        return False
    
    def supports_vision(self) -> bool:
        return False


# Register provider
ollama_provider = OllamaProvider()
registry.register(ollama_provider)
