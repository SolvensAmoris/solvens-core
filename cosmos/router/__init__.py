"""
Provider Router for COSMOS

Routes tasks to optimal providers based on policy.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProviderCapability(Enum):
    """Capabilities that providers can have."""
    REASONING = "reasoning"
    CODE_GEN = "code_gen"
    VISION = "vision"
    TEXT = "text"
    EMBEDDINGS = "embeddings"
    SPEECH = "speech"
    LOCAL = "local"  # Runs offline


@dataclass
class Provider:
    """
    Represents an AI provider.
    
    Attributes:
        name: Provider name (e.g., "openai", "claude")
        model: Model name (e.g., "gpt-4", "claude-3-sonnet")
        capabilities: List of capabilities this provider has
        cost_per_1k_tokens: Cost in USD per 1000 tokens
        latency_ms_avg: Average latency in milliseconds
        available: Whether the provider is currently available
    """
    
    name: str
    model: str
    capabilities: list[ProviderCapability]
    cost_per_1k_tokens: float
    latency_ms_avg: int
    available: bool = True
    
    def supports(self, capability: ProviderCapability) -> bool:
        """Check if this provider supports a capability."""
        return capability in self.capabilities


class RoutingPolicy(Enum):
    """Policy for routing tasks to providers."""
    COST_OPTIMIZED = "cost"  # Minimize cost
    LATENCY_OPTIMIZED = "latency"  # Minimize latency
    CAPABILITY_MATCH = "capability"  # Match required capability
    BALANCED = "balanced"  # Balance cost and latency


@dataclass
class RouteRequest:
    """Request to route a task to a provider."""
    task_type: str
    required_capabilities: list[ProviderCapability]
    priority: int = 0  # Higher = more important


@dataclass 
class RouteResult:
    """Result of routing decision."""
    provider: Optional[Provider]
    policy_used: RoutingPolicy
    reason: str


class ProviderRouter:
    """
    Routes tasks to optimal providers based on policy.
    
    Features:
    - Cost optimization
    - Latency optimization
    - Capability matching
    - Automatic fallback
    """
    
    def __init__(self, policy: RoutingPolicy = RoutingPolicy.BALANCED):
        self.policy = policy
        self.providers: dict[str, Provider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default providers."""
        self.register_provider(Provider(
            name="openai",
            model="gpt-4o",
            capabilities=[ProviderCapability.REASONING, ProviderCapability.CODE_GEN, 
                         ProviderCapability.VISION, ProviderCapability.TEXT],
            cost_per_1k_tokens=0.015,
            latency_ms_avg=500
        ))
        
        self.register_provider(Provider(
            name="anthropic",
            model="claude-3-sonnet",
            capabilities=[ProviderCapability.REASONING, ProviderCapability.CODE_GEN,
                         ProviderCapability.TEXT, ProviderCapability.EMBEDDINGS],
            cost_per_1k_tokens=0.015,
            latency_ms_avg=800
        ))
        
        self.register_provider(Provider(
            name="google",
            model="gemini-1.5-pro",
            capabilities=[ProviderCapability.REASONING, ProviderCapability.CODE_GEN,
                         ProviderCapability.VISION, ProviderCapability.TEXT],
            cost_per_1k_tokens=0.007,
            latency_ms_avg=400
        ))
        
        self.register_provider(Provider(
            name="ollama",
            model="llama3",
            capabilities=[ProviderCapability.REASONING, ProviderCapability.CODE_GEN,
                         ProviderCapability.TEXT, ProviderCapability.LOCAL],
            cost_per_1k_tokens=0.0,  # Free when running locally
            latency_ms_avg=200
        ))
        
        self.register_provider(Provider(
            name="deepseek",
            model="deepseek-chat",
            capabilities=[ProviderCapability.REASONING, ProviderCapability.CODE_GEN,
                         ProviderCapability.TEXT],
            cost_per_1k_tokens=0.001,
            latency_ms_avg=600
        ))
    
    def register_provider(self, provider: Provider) -> None:
        """Register a new provider."""
        self.providers[provider.name] = provider
    
    def unregister_provider(self, name: str) -> None:
        """Unregister a provider."""
        if name in self.providers:
            del self.providers[name]
    
    def get_provider(self, name: str) -> Optional[Provider]:
        """Get a provider by name."""
        return self.providers.get(name)
    
    def list_providers(self) -> list[Provider]:
        """List all registered providers."""
        return list(self.providers.values())
    
    def route(self, request: RouteRequest) -> RouteResult:
        """
        Route a task to the optimal provider.
        
        Args:
            request: RouteRequest with task details
            
        Returns:
            RouteResult with the selected provider and reasoning
        """
        # Filter by capability first
        candidates = self._filter_by_capability(request.required_capabilities)
        
        if not candidates:
            return RouteResult(
                provider=None,
                policy_used=self.policy,
                reason="No provider supports required capabilities"
            )
        
        # Filter by availability
        candidates = [p for p in candidates if p.available]
        
        if not candidates:
            return RouteResult(
                provider=None,
                policy_used=self.policy,
                reason="No provider available"
            )
        
        # Apply routing policy
        if self.policy == RoutingPolicy.COST_OPTIMIZED:
            return self._route_cost_optimized(candidates)
        elif self.policy == RoutingPolicy.LATENCY_OPTIMIZED:
            return self._route_latency_optimized(candidates)
        elif self.policy == RoutingPolicy.CAPABILITY_MATCH:
            return self._route_capability_match(candidates, request.required_capabilities)
        else:  # BALANCED
            return self._route_balanced(candidates)
    
    def _filter_by_capability(self, capabilities: list[ProviderCapability]) -> list[Provider]:
        """Filter providers by required capabilities."""
        if not capabilities:
            return self.list_providers()
        
        return [
            p for p in self.providers.values()
            if all(p.supports(cap) for cap in capabilities)
        ]
    
    def _route_cost_optimized(self, candidates: list[Provider]) -> RouteResult:
        """Route to cheapest provider."""
        candidates.sort(key=lambda p: p.cost_per_1k_tokens)
        provider = candidates[0]
        return RouteResult(
            provider=provider,
            policy_used=RoutingPolicy.COST_OPTIMIZED,
            reason=f"Selected {provider.name} (${provider.cost_per_1k_tokens}/1K tokens)"
        )
    
    def _route_latency_optimized(self, candidates: list[Provider]) -> RouteResult:
        """Route to fastest provider."""
        candidates.sort(key=lambda p: p.latency_ms_avg)
        provider = candidates[0]
        return RouteResult(
            provider=provider,
            policy_used=RoutingPolicy.LATENCY_OPTIMIZED,
            reason=f"Selected {provider.name} ({provider.latency_ms_avg}ms avg)"
        )
    
    def _route_capability_match(self, candidates: list[Provider], 
                                capabilities: list[ProviderCapability]) -> RouteResult:
        """Route to provider with best capability match."""
        # Score by how many capabilities match
        def score(p: Provider) -> int:
            return sum(1 for c in capabilities if p.supports(c))
        
        candidates.sort(key=score, reverse=True)
        provider = candidates[0]
        return RouteResult(
            provider=provider,
            policy_used=RoutingPolicy.CAPABILITY_MATCH,
            reason=f"Selected {provider.name} with best capability match"
        )
    
    def _route_balanced(self, candidates: list[Provider]) -> RouteResult:
        """Route balancing cost and latency."""
        # Normalize and combine scores
        max_cost = max(p.cost_per_1k_tokens for p in candidates) or 1
        max_latency = max(p.latency_ms_avg for p in candidates) or 1
        
        def score(p: Provider) -> float:
            cost_score = 1 - (p.cost_per_1k_tokens / max_cost)
            latency_score = 1 - (p.latency_ms_avg / max_latency)
            return (cost_score + latency_score) / 2
        
        candidates.sort(key=score, reverse=True)
        provider = candidates[0]
        return RouteResult(
            provider=provider,
            policy_used=RoutingPolicy.BALANCED,
            reason=f"Selected {provider.name} (balanced score)"
        )
    
    def get_fallback(self, original: Provider) -> Optional[Provider]:
        """
        Get a fallback provider when the original is unavailable.
        
        Tries to find a provider with similar capabilities at higher cost.
        """
        candidates = [
            p for p in self.providers.values()
            if p.name != original.name 
            and p.available
            and any(original.supports(c) for c in p.capabilities)
        ]
        
        if not candidates:
            return None
        
        # Prefer cheapest available fallback
        candidates.sort(key=lambda p: p.cost_per_1k_tokens)
        return candidates[0]
