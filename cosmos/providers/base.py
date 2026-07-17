"""
SOLVENS Provider Interface

Abstract interface for all LLM providers.
All provider-specific code must implement this interface.

This solves VENDOR_LOCK by ensuring no code depends on
specific provider implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncIterator, Any
from enum import Enum


class ProviderType(str, Enum):
    """Provider types supported."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


@dataclass
class Message:
    """Chat message."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class CompletionResult:
    """Result of a completion request."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    raw_response: Optional[dict] = None


@dataclass
class EmbeddingResult:
    """Result of an embedding request."""
    embedding: list[float]
    model: str
    provider: str
    tokens: int


@dataclass  
class StreamingChunk:
    """Chunk of a streaming response."""
    content: str
    delta: str
    done: bool


class CompletionError(Exception):
    """Raised when all providers fail."""
    pass


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    All providers MUST implement this interface.
    No provider-specific code should exist outside provider implementations.
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass
    
    @property
    def supported_models(self) -> list[str]:
        """Return list of supported models."""
        return []
    
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResult:
        """
        Send a completion request.
        
        Args:
            messages: List of chat messages
            model: Model to use (optional, uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            CompletionResult with response
        """
        pass
    
    @abstractmethod
    async def complete_stream(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """
        Send a streaming completion request.
        
        Args:
            messages: List of chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Yields:
            StreamingChunk for each token
        """
        pass
    
    @abstractmethod
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResult:
        """
        Get embeddings for text.
        
        Args:
            text: Text to embed
            model: Model to use
        
        Returns:
            EmbeddingResult with embeddings
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass
    
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token usage.
        
        Override this in subclasses with actual pricing.
        """
        return 0.0  # Default: free
    
    def supports_vision(self) -> bool:
        """Check if provider supports vision."""
        return False
    
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling."""
        return False


class ProviderRegistry:
    """
    Registry for all providers.
    
    Provides a single entry point for accessing any provider,
    solving VENDOR_LOCK by abstracting provider selection.
    """
    
    def __init__(self):
        self._providers: dict[ProviderType, BaseProvider] = {}
        self._default_provider: Optional[ProviderType] = None
    
    def register(self, provider: BaseProvider) -> None:
        """Register a provider."""
        self._providers[provider.provider_type] = provider
    
    def get(self, provider_type: ProviderType) -> Optional[BaseProvider]:
        """Get a provider by type."""
        return self._providers.get(provider_type)
    
    def get_default(self) -> Optional[BaseProvider]:
        """Get the default provider."""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        # Return first available
        if self._providers:
            return next(iter(self._providers.values()))
        return None
    
    def set_default(self, provider_type: ProviderType) -> None:
        """Set the default provider."""
        self._default_provider = provider_type
    
    def list_providers(self) -> list[ProviderType]:
        """List all registered providers."""
        return list(self._providers.keys())
    
    def list_available(self) -> list[ProviderType]:
        """List all providers that pass health check."""
        import asyncio
        available = []
        for ptype, provider in self._providers.items():
            try:
                if asyncio.get_event_loop().run_until_complete(provider.health_check()):
                    available.append(ptype)
            except:
                pass
        return available


# Singleton registry
registry = ProviderRegistry()
