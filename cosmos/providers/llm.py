"""
SOLVENS Unified LLM Interface

Provides a single interface for all LLM providers with automatic failover.
This is the ONLY entry point for LLM calls, solving VENDOR_LOCK.
"""

import os
import asyncio
import logging
from typing import Optional, AsyncIterator, Callable

from .base import (
    BaseProvider,
    ProviderType,
    Message,
    CompletionResult,
    StreamingChunk,
    CompletionError,
    registry,
)
# CompletionError is now defined in base.py

logger = logging.getLogger(__name__)


class LLMInterface:
    """
    Unified interface for all LLM providers.
    
    Features:
    - Single entry point for all LLM calls
    - Automatic failover between providers
    - Cost-based routing
    - Circuit breaker integration
    """
    
    def __init__(self):
        self._providers: dict[ProviderType, BaseProvider] = {}
        self._load_providers()
    
    def _load_providers(self) -> None:
        """Load all available providers."""
        # Provider loading is optional - they can be registered manually
        # This prevents import errors from breaking the system
        
        # Set default preference order
        self._default = ProviderType.OPENAI  # Can be overridden
    
    def get_provider(self, provider_type: Optional[ProviderType] = None) -> BaseProvider:
        """Get a provider by type."""
        ptype = provider_type or self._default
        if not ptype:
            raise ValueError("No providers available")
        return self._providers.get(ptype)
    
    async def complete(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        provider: Optional[ProviderType] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        fallback: bool = True,
        **kwargs
    ) -> CompletionResult:
        """
        Send a completion request with optional failover.
        
        Args:
            messages: Chat messages
            model: Specific model to use
            provider: Preferred provider (auto-selected if not specified)
            fallback: Whether to try other providers on failure
            **kwargs: Additional provider-specific args
        
        Returns:
            CompletionResult from successful provider
        
        Raises:
            CompletionError: If all providers fail
        """
        # Determine provider order (preference + fallback)
        if provider and provider in self._providers:
            providers_to_try = [provider]
            if fallback:
                providers_to_try.extend(
                    p for p in self._providers if p != provider
                )
        else:
            providers_to_try = list(self._providers.keys())
        
        errors = []
        
        for ptype in providers_to_try:
            prov = self._providers[ptype]
            
            try:
                # Check if provider is healthy
                if not await prov.health_check():
                    logger.warning(f"Provider {ptype} unhealthy, skipping")
                    continue
                
                # Execute
                result = await prov.complete(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                logger.info(f"Completed with {ptype}: {result.output_tokens} tokens")
                return result
                
            except Exception as e:
                logger.warning(f"Provider {ptype} failed: {e}")
                errors.append((ptype, str(e)))
                continue
        
        # All providers failed
        raise CompletionError(
            f"All providers failed. Errors: {errors}"
        )
    
    async def complete_stream(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        provider: Optional[ProviderType] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        fallback: bool = True,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """
        Send streaming completion with failover.
        
        Note: Streaming doesn't support transparent failover.
        Falls back to non-streaming if streaming fails.
        """
        ptype = provider or self._default
        
        if not ptype or ptype not in self._providers:
            raise ValueError(f"Provider {provider} not available")
        
        prov = self._providers[ptype]
        
        try:
            # Try streaming first
            async for chunk in prov.complete_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield chunk
                
        except Exception as e:
            logger.warning(f"Streaming failed with {ptype}, falling back to non-streaming")
            
            # Fall back to non-streaming
            result = await self.complete(
                messages=messages,
                model=model,
                provider=ptype,
                temperature=temperature,
                max_tokens=max_tokens,
                fallback=False,
                **kwargs
            )
            
            # Yield as single chunk
            yield StreamingChunk(
                content=result.content,
                delta=result.content,
                done=True,
            )
    
    def select_cheapest(self, task_complexity: str = "medium") -> ProviderType:
        """
        Select the cheapest capable provider.
        
        For free-tier tasks, prefer Ollama.
        For complex tasks, prefer Claude/GPT-4.
        """
        if task_complexity in ("simple", "medium"):
            if ProviderType.OLLAMA in self._providers:
                return ProviderType.OLLAMA
        
        # Complex tasks: prefer Anthropic > OpenAI > Ollama
        if ProviderType.ANTHROPIC in self._providers:
            return ProviderType.ANTHROPIC
        if ProviderType.OPENAI in self._providers:
            return ProviderType.OPENAI
        if ProviderType.OLLAMA in self._providers:
            return ProviderType.OLLAMA
        
        return list(self._providers.keys())[0] if self._providers else ProviderType.OPENAI
    
    def list_providers(self) -> list[ProviderType]:
        """List all available providers."""
        return list(self._providers.keys())
    
    async def health_report(self) -> dict:
        """Get health status of all providers."""
        report = {}
        
        for ptype, prov in self._providers.items():
            try:
                healthy = await prov.health_check()
                report[ptype.value] = {
                    "available": healthy,
                    "default": ptype == self._default,
                }
            except Exception as e:
                report[ptype.value] = {
                    "available": False,
                    "error": str(e),
                }
        
        return report


# Singleton instance
llm = LLMInterface()
