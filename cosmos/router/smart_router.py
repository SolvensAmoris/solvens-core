"""
cosmos/router/smart_router.py
===============================

SMART ROUTER v0.2
=================

Routes tasks to optimal provider based on:
- Task type (code, research, vision, etc.)
- Cost efficiency
- Latency requirements
- Provider availability

Providers: Grok (primary) + Ollama (fallback)

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger("cosmos.router")


# ============================================================
# PROVIDER TYPES
# ============================================================

class ProviderType(Enum):
    """Tipos de provider."""
    GROK = "grok"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"


class TaskType(Enum):
    """Tipos de task para routing."""
    CODE = "code"
    RESEARCH = "research"
    VISION = "vision"
    REASONING = "reasoning"
    FAST = "fast"
    CREATIVE = "creative"
    LEGAL = "legal"
    ANALYSIS = "analysis"


@dataclass
class ProviderConfig:
    """Configuración de provider."""
    name: str
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "default"
    cost_input: float = 0.0  # per 1M tokens
    cost_output: float = 0.0
    latency_ms: float = 1000.0  # average latency
    max_tokens: int = 4096
    enabled: bool = True
    priority: int = 100  # lower = higher priority


@dataclass
class RoutingResult:
    """Resultado de routing."""
    provider: ProviderType
    model: str
    estimated_cost: float
    estimated_latency_ms: float
    reason: str


# ============================================================
# PROVIDER BASE
# ============================================================

class Provider(ABC):
    """Base class para providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._available = True
        self._stats = {
            "requests": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "failures": 0,
            "avg_latency_ms": 0,
        }
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Ejecuta chat completion."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    @property
    def is_available_sync(self) -> bool:
        """Sync check availability."""
        return self._available
    
    def record_usage(self, input_tokens: int, output_tokens: int, latency_ms: float, cost: float):
        """Registra uso para stats."""
        self._stats["requests"] += 1
        self._stats["total_cost"] += cost
        self._stats["total_tokens"] += input_tokens + output_tokens
        self._stats["total_latency_ms"] = (
            (self._stats.get("avg_latency_ms", 0) * (self._stats["requests"] - 1) + latency_ms)
            / self._stats["requests"]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "available": self._available}


# ============================================================
# GROK PROVIDER
# ============================================================

class GrokProvider(Provider):
    """Provider para Grok API."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("GROK_API_KEY")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chat con Grok."""
        start = time.time()
        
        try:
            # Simulated for demo - replace with real API call
            await asyncio.sleep(0.1)  # Simulate network
            
            response = {
                "content": f"[Grok] Response to: {messages[-1]['content'][:50]}...",
                "model": self.config.model,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                },
                "latency_ms": (time.time() - start) * 1000,
            }
            
            cost = (100 / 1_000_000) * self.config.cost_input + \
                   (50 / 1_000_000) * self.config.cost_output
            
            self.record_usage(
                input_tokens=100,
                output_tokens=50,
                latency_ms=response["latency_ms"],
                cost=cost
            )
            
            return response
            
        except Exception as e:
            self._stats["failures"] += 1
            raise
    
    async def is_available(self) -> bool:
        """Check Grok availability."""
        if not self.api_key:
            self._available = False
            return False
        return True


# ============================================================
# OLLAMA PROVIDER
# ============================================================

class OllamaProvider(Provider):
    """Provider para Ollama local."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.model = config.model or "llama3"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chat con Ollama."""
        start = time.time()
        
        try:
            # Simulated for demo
            await asyncio.sleep(0.05)  # Faster than cloud
            
            response = {
                "content": f"[Ollama] Response to: {messages[-1]['content'][:50]}...",
                "model": self.model,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                },
                "latency_ms": (time.time() - start) * 1000,
            }
            
            # Ollama is free (local)
            self.record_usage(
                input_tokens=100,
                output_tokens=50,
                latency_ms=response["latency_ms"],
                cost=0.0
            )
            
            return response
            
        except Exception as e:
            self._stats["failures"] += 1
            self._available = False
            raise
    
    async def is_available(self) -> bool:
        """Check Ollama availability."""
        try:
            # Could ping Ollama API here
            return True
        except:
            self._available = False
            return False


# ============================================================
# SMART ROUTER
# ============================================================

class SmartRouter:
    """
    Router inteligente que selecciona el mejor provider.
    
    Strategy:
    1. Match task type to provider strengths
    2. Score by cost + latency
    3. Fallback chain for reliability
    """
    
    # Task type to provider mapping
    TASK_PROVIDER_MAP = {
        TaskType.CODE: [ProviderType.GROK, ProviderType.OLLAMA],
        TaskType.RESEARCH: [ProviderType.GROK, ProviderType.ANTHROPIC],
        TaskType.VISION: [ProviderType.GOOGLE, ProviderType.OPENAI],
        TaskType.REASONING: [ProviderType.GROK, ProviderType.ANTHROPIC],
        TaskType.FAST: [ProviderType.OLLAMA, ProviderType.GROK],
        TaskType.CREATIVE: [ProviderType.GROK, ProviderType.OPENAI],
        TaskType.LEGAL: [ProviderType.GROK, ProviderType.ANTHROPIC],
        TaskType.ANALYSIS: [ProviderType.GROK, ProviderType.DEEPSEEK],
    }
    
    def __init__(self):
        self._providers: Dict[ProviderType, Provider] = {}
        self._task_types: Dict[str, TaskType] = {}
        self._init_default_providers()
    
    def _init_default_providers(self):
        """Inicializa providers por defecto."""
        # Grok (primary)
        grok_config = ProviderConfig(
            name="Grok",
            provider_type=ProviderType.GROK,
            model="grok-2",
            cost_input=2.0,  # $2/1M input
            cost_output=10.0,  # $10/1M output
            latency_ms=2000,
            priority=1
        )
        self.register_provider(GrokProvider(grok_config))
        
        # Ollama (fallback, free)
        ollama_config = ProviderConfig(
            name="Ollama",
            provider_type=ProviderType.OLLAMA,
            model="llama3",
            cost_input=0.0,
            cost_output=0.0,
            latency_ms=500,
            priority=2
        )
        self.register_provider(OllamaProvider(ollama_config))
    
    def register_provider(self, provider: Provider):
        """Registra un provider."""
        self._providers[provider.config.provider_type] = provider
        logger.info(f"Provider registered: {provider.config.name}")
    
    def register_task_keywords(self, keywords: Dict[str, str]):
        """Registra keywords para auto-detección de task type."""
        for keyword, task_type in keywords.items():
            self._task_types[keyword.lower()] = TaskType(task_type)
    
    def detect_task_type(self, prompt: str) -> TaskType:
        """Detecta el tipo de task basado en keywords."""
        prompt_lower = prompt.lower()
        
        # Check registered keywords
        for keyword, task_type in self._task_types.items():
            if keyword in prompt_lower:
                return task_type
        
        # Default heuristics
        if any(w in prompt_lower for w in ["code", "python", "javascript", "debug", "function"]):
            return TaskType.CODE
        elif any(w in prompt_lower for w in ["research", "find", "search", "analyze"]):
            return TaskType.RESEARCH
        elif any(w in prompt_lower for w in ["legal", "law", "court", "act", "regulation"]):
            return TaskType.LEGAL
        elif any(w in prompt_lower for w in ["image", "photo", "picture", "vision"]):
            return TaskType.VISION
        else:
            return TaskType.FAST
    
    def score_provider(
        self,
        provider: Provider,
        task_type: TaskType,
        estimated_tokens: int = 1000
    ) -> float:
        """
        Score un provider para un task.
        
        Lower score = better.
        """
        if not provider.is_available_sync:
            return float('inf')
        
        # Cost score (40%)
        estimated_cost = (
            estimated_tokens * 0.5 * provider.config.cost_input +
            estimated_tokens * 0.5 * provider.config.cost_output
        ) / 1_000_000
        cost_score = estimated_cost * 100
        
        # Latency score (30%)
        latency_score = provider.config.latency_ms / 100
        
        # Priority score (20%)
        priority_score = provider.config.priority * 10
        
        # Availability bonus (10%)
        availability_score = 0
        
        # Task match bonus
        preferred = self.TASK_PROVIDER_MAP.get(task_type, [])
        if provider.config.provider_type in preferred:
            availability_score = -50
        
        return cost_score + latency_score + priority_score + availability_score
    
    async def route(
        self,
        prompt: str,
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[ProviderType] = None,
        estimated_tokens: int = 1000
    ) -> RoutingResult:
        """
        Routes a request to the best provider.
        
        Returns:
            RoutingResult con provider seleccionado
        """
        # Detect task type if not provided
        if task_type is None:
            task_type = self.detect_task_type(prompt)
        
        # Get candidates
        if preferred_provider:
            candidates = [preferred_provider]
        else:
            candidate_types = self.TASK_PROVIDER_MAP.get(task_type, [ProviderType.GROK])
            candidates = [pt for pt in candidate_types if pt in self._providers]
            if not candidates:
                candidates = list(self._providers.keys())
        
        # Score each provider
        scored = []
        for pt in candidates:
            provider = self._providers[pt]
            score = self.score_provider(provider, task_type, estimated_tokens)
            scored.append((score, provider))
        
        # Sort by score
        scored.sort(key=lambda x: x[0])
        
        # Try providers in order
        for score, provider in scored:
            if await provider.is_available():
                return RoutingResult(
                    provider=provider.config.provider_type,
                    model=provider.config.model,
                    estimated_cost=score,
                    estimated_latency_ms=provider.config.latency_ms,
                    reason=f"{task_type.value} → {provider.config.name}"
                )
        
        # No provider available
        raise RuntimeError("No providers available")
    
    async def execute(
        self,
        prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Route y ejecuta request.
        
        Returns:
            Response del provider
        """
        routing = await self.route(prompt)
        provider = self._providers[routing.provider]
        
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        
        result = await provider.chat(messages, **kwargs)
        result["routing"] = routing
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene stats de todos los providers."""
        return {
            "providers": {
                pt.value: p.get_stats()
                for pt, p in self._providers.items()
            }
        }


# ============================================================
# GLOBAL ROUTER
# ============================================================

_router: Optional[SmartRouter] = None


def get_router() -> SmartRouter:
    """Obtiene o crea el router global."""
    global _router
    if _router is None:
        _router = SmartRouter()
    return _router


# ============================================================
# DEMO
# ============================================================

async def demo():
    """Demo del Smart Router."""
    print("=" * 60)
    print("SMART ROUTER v0.2 DEMO")
    print("=" * 60)
    
    router = get_router()
    
    # Test cases
    test_cases = [
        ("Write a Python function to sort a list", TaskType.CODE),
        ("Research the latest AI regulations in EU", TaskType.RESEARCH),
        ("Analyze this legal contract for risks", TaskType.LEGAL),
        ("What's the weather today?", None),  # Auto-detect
    ]
    
    print("\n[Routing Examples]")
    for prompt, expected_type in test_cases:
        routing = await router.route(prompt, task_type=expected_type)
        detected = router.detect_task_type(prompt)
        print(f"\n  Prompt: {prompt[:50]}...")
        print(f"  Detected: {detected.value}")
        print(f"  Route: {routing.provider.value} ({routing.model})")
        print(f"  Reason: {routing.reason}")
    
    # Execute
    print("\n[Execute Example]")
    result = await router.execute("Explain quantum computing")
    print(f"  Response: {result['content'][:60]}...")
    print(f"  Latency: {result.get('latency_ms', 0):.0f}ms")
    
    print("\n[Stats]")
    stats = router.get_stats()
    for provider, pstats in stats["providers"].items():
        print(f"  {provider}: {pstats['requests']} requests, ${pstats['total_cost']:.4f}")
    
    print("\n" + "=" * 60)
    print("Router ready!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
