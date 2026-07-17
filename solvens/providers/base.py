"""Provider base interface for SOLVENS CORE.

All AI providers implement this interface to ensure compatibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, TypeVar

from solvens.core.base import BaseModel, BaseService
from solvens.core.types import Message, Model, ModelCapability, ProviderType, Response, TokenUsage


T = TypeVar("T")


@dataclass
class ChatOptions:
    """Options for chat completion.
    
    Attributes:
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        stop: Stop sequences
        stream: Enable streaming responses
        seed: Random seed for reproducibility
    """
    
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | None = None
    stream: bool = False
    seed: int | None = None


@dataclass
class EmbeddingsOptions:
    """Options for embeddings generation."""
    
    model: str | None = None
    dimensions: int | None = None


class ProviderClient(ABC):
    """Abstract base class for all AI providers.
    
    All providers must implement these methods to be compatible
    with SOLVENS CORE's agent system.
    
    Example:
        class OpenAIProvider(ProviderClient):
            async def chat(self, messages, **options) -> Response:
                # Implementation
                ...
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        ...
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return human-readable provider name."""
        ...
    
    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming."""
        return True
    
    @property
    def supports_vision(self) -> bool:
        """Whether this provider supports vision."""
        return False
    
    @property
    def supports_function_calling(self) -> bool:
        """Whether this provider supports function calling."""
        return False
    
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        **options: Any,
    ) -> Response:
        """Send a chat completion request.
        
        Args:
            messages: List of conversation messages
            model: Model ID (uses default if None)
            **options: Additional provider-specific options
            
        Returns:
            Response with generated content
        """
        ...
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        **options: Any,
    ) -> AsyncIterator[str]:
        """Send a streaming chat completion request.
        
        Args:
            messages: List of conversation messages
            model: Model ID
            **options: Additional provider-specific options
            
        Yields:
            Text chunks as they are generated
        """
        ...
    
    @abstractmethod
    async def embeddings(
        self,
        texts: list[str],
        model: str | None = None,
        **options: Any,
    ) -> list[list[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model ID
            **options: Additional options
            
        Returns:
            List of embedding vectors
        """
        ...
    
    async def vision(
        self,
        image: str | bytes,
        prompt: str,
        model: str | None = None,
        **options: Any,
    ) -> Response:
        """Process image with vision model.
        
        Args:
            image: Image URL or base64 data
            prompt: Question about the image
            model: Vision model ID
            **options: Additional options
            
        Returns:
            Response describing the image
        """
        if not self.supports_vision:
            raise NotImplementedError(f"{self.provider_name} does not support vision")
        raise NotImplementedError("Vision not implemented")

    async def function_calling(
        self,
        messages: list[Message],
        functions: list[dict[str, Any]],
        model: str | None = None,
        **options: Any,
    ) -> Response:
        """Execute a function call.
        
        Args:
            messages: Conversation messages
            functions: Available functions
            model: Model ID
            **options: Additional options
            
        Returns:
            Response with function call
        """
        if not self.supports_function_calling:
            raise NotImplementedError(f"{self.provider_name} does not support function calling")
        raise NotImplementedError("Function calling not implemented")
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available.
        
        Returns:
            True if provider is healthy
        """
        ...
    
    async def close(self) -> None:
        """Clean up provider resources."""
        pass


class ProviderAdapter(BaseService[ProviderClient]):
    """Adapter for AI providers with lifecycle management.
    
    Wraps a ProviderClient with initialization and configuration.
    """
    
    def __init__(
        self,
        name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **config: Any,
    ):
        super().__init__()
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.config = config
        self._client: ProviderClient | None = None

    @abstractmethod
    async def _create_client(self) -> ProviderClient:
        """Create the underlying provider client."""
        ...

    async def initialize(self) -> None:
        """Initialize the provider client."""
        self._client = await self._create_client()
        self._resource = self._client

    async def shutdown(self) -> None:
        """Shutdown and cleanup."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def is_healthy(self) -> bool:
        """Check if provider is healthy."""
        return self._client is not None

    async def chat(self, messages: list[Message], **kwargs: Any) -> Response:
        """Chat via the wrapped client."""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        return await self._client.chat(messages, **kwargs)

    async def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Generate embeddings via the wrapped client."""
        if not self._client:
            raise RuntimeError("Provider not initialized")
        return await self._client.embeddings(texts, **kwargs)
