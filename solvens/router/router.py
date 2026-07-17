"""Capability Router - Routes tasks to optimal providers based on capabilities."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from solvens.core.base import BaseModel, BaseService
from solvens.core.exceptions import (
    NoProviderAvailableError,
    ProviderError,
    RouterError,
)
from solvens.core.types import (
    Message,
    Model,
    ModelCapability,
    Provider,
    ProviderType,
    Response,
    TaskPriority,
)

logger = structlog.get_logger(__name__)


@dataclass
class RoutingRule:
    """A routing rule that matches tasks to providers.
    
    Attributes:
        name: Rule name
        patterns: List of regex patterns to match
        capability: Required capability
        provider: Preferred provider type
        model: Preferred model ID
        priority: Rule priority (higher = evaluated first)
        cost_weight: Cost optimization weight (0-1)
        quality_weight: Quality weight (0-1)
    """
    
    name: str
    patterns: list[str]
    capability: ModelCapability | None = None
    provider: ProviderType | None = None
    model: str | None = None
    priority: int = 0
    cost_weight: float = 0.5
    quality_weight: float = 0.5
    enabled: bool = True

    def matches(self, content: str) -> bool:
        """Check if content matches any pattern."""
        for pattern in self.patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False


@dataclass
class RoutingResult:
    """Result of a routing decision.
    
    Attributes:
        provider: Selected provider
        model: Selected model
        rule: Matching rule
        reasoning: Why this provider was selected
    """
    
    provider: Provider
    model: Model
    rule: RoutingRule | None = None
    reasoning: str = ""


class ProviderRegistry:
    """Registry of available providers and models."""
    
    def __init__(self):
        self._providers: dict[ProviderType, Provider] = {}
        self._models: dict[str, tuple[Model, ProviderType]] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider."""
        self._providers[provider.type] = provider
        for model in provider.models:
            self._models[model.id] = (model, provider.type)
        logger.info("Provider registered", provider=provider.name, type=provider.type)

    def unregister(self, provider_type: ProviderType) -> None:
        """Unregister a provider."""
        if provider_type in self._providers:
            provider = self._providers.pop(provider_type)
            for model in provider.models:
                self._models.pop(model.id, None)
            logger.info("Provider unregistered", type=provider_type)

    def get_provider(self, provider_type: ProviderType) -> Provider | None:
        """Get a provider by type."""
        return self._providers.get(provider_type)

    def get_model(self, model_id: str) -> tuple[Model, ProviderType] | None:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_providers(self) -> list[Provider]:
        """List all registered providers."""
        return list(self._providers.values())

    def list_models(
        self,
        capability: ModelCapability | None = None,
        provider: ProviderType | None = None,
    ) -> list[Model]:
        """List models with optional filtering."""
        models = []
        
        for model, provider_type in self._models.values():
            if provider and provider_type != provider:
                continue
            if capability and capability not in model.capabilities:
                continue
            models.append(model)
        
        return models

    def find_models_for_capability(
        self,
        capability: ModelCapability,
    ) -> list[tuple[Model, Provider]]:
        """Find all models that support a capability."""
        results = []
        
        for provider in self._providers.values():
            for model in provider.models:
                if capability in model.capabilities:
                    results.append((model, provider))
        
        return results


class CapabilityRouter(BaseService[ProviderRegistry]):
    """Routes tasks to optimal providers based on capabilities and rules.
    
    The router analyzes task requirements and selects the best provider
    using configurable routing rules.
    
    Routing Logic:
    - Code → Claude
    - Research → Sakana
    - Documentation → Gemini
    - Reasoning → GPT
    - Offline → Ollama
    - Video → Pollo AI
    """
    
    def __init__(
        self,
        cost_optimization: bool = True,
        enable_fallback: bool = True,
    ):
        super().__init__()
        self.cost_optimization = cost_optimization
        self.enable_fallback = enable_fallback
        self._rules: list[RoutingRule] = []
        self._default_provider: ProviderType = ProviderType.OPENAI
        self._fallback_provider: ProviderType = ProviderType.OLLAMA
        self._routing_history: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the router."""
        logger.info("Initializing CapabilityRouter")
        self._resource = ProviderRegistry()
        self._load_default_rules()
        logger.info("CapabilityRouter initialized", rules=len(self._rules))

    async def shutdown(self) -> None:
        """Shutdown the router."""
        logger.info("Shutting down CapabilityRouter")
        self._routing_history.clear()

    def _load_default_rules(self) -> None:
        """Load default routing rules."""
        from solvens.router.rules import DefaultRoutingRules
        self._rules = DefaultRoutingRules.get_default_rules()

    # === Public API ===

    def add_rule(self, rule: RoutingRule) -> str:
        """Add a routing rule.
        
        Args:
            rule: Rule to add
            
        Returns:
            Rule ID
        """
        rule_id = str(uuid.uuid4())
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info("Routing rule added", rule=rule.name, priority=rule.priority)
        return rule_id

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a routing rule by name."""
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.name != rule_name]
        removed = len(self._rules) < original_count
        if removed:
            logger.info("Routing rule removed", rule=rule_name)
        return removed

    def register_provider(self, provider: Provider) -> None:
        """Register a provider."""
        self._resource.register(provider)

    def unregister_provider(self, provider_type: ProviderType) -> None:
        """Unregister a provider."""
        self._resource.unregister(provider_type)

    async def route(
        self,
        messages: list[Message],
        preferred_model: str | None = None,
        preferred_provider: str | None = None,
        required_capability: ModelCapability | None = None,
    ) -> str:
        """Route a message to the best provider.
        
        Args:
            messages: Conversation messages
            preferred_model: Preferred model ID
            preferred_provider: Preferred provider type
            required_capability: Required capability
            
        Returns:
            Provider response content
            
        Raises:
            NoProviderAvailableError: If no provider is available
        """
        # Get the last user message for routing
        content = self._get_routing_content(messages)
        
        # Find matching rule
        rule = self._find_matching_rule(content)
        
        # Select provider
        provider_type, model = self._select_provider(
            content=content,
            preferred_model=preferred_model,
            preferred_provider=preferred_provider,
            required_capability=required_capability,
            rule=rule,
        )
        
        # Log routing decision
        self._log_routing(content, provider_type, model, rule)
        
        # Call the provider (placeholder for actual implementation)
        response = await self._call_provider(
            provider_type=provider_type,
            model=model,
            messages=messages,
        )
        
        return response

    async def route_to_provider(
        self,
        provider_type: ProviderType,
        model: str | None,
        messages: list[Message],
    ) -> str:
        """Route to a specific provider.
        
        Args:
            provider_type: Target provider
            model: Model ID (uses default if None)
            messages: Conversation messages
            
        Returns:
            Provider response
        """
        provider = self._resource.get_provider(provider_type)
        if not provider:
            raise RouterError(f"Provider {provider_type} not registered")
        
        selected_model = None
        if model:
            model_obj, _ = self._resource.get_model(model)
            selected_model = model_obj
        else:
            selected_model = provider.models[0] if provider.models else None
        
        if not selected_model:
            raise RouterError(f"No model available for provider {provider_type}")
        
        return await self._call_provider(provider_type, selected_model, messages)

    # === Routing Logic ===

    def _get_routing_content(self, messages: list[Message]) -> str:
        """Extract content for routing from messages."""
        for message in reversed(messages):
            if message.role in (Message.role.USER, Message.role.SYSTEM):
                return message.content
        return ""

    def _find_matching_rule(self, content: str) -> RoutingRule | None:
        """Find the first matching rule for content."""
        for rule in self._rules:
            if rule.enabled and rule.matches(content):
                return rule
        return None

    def _select_provider(
        self,
        content: str,
        preferred_model: str | None,
        preferred_provider: str | None,
        required_capability: ModelCapability | None,
        rule: RoutingRule | None,
    ) -> tuple[ProviderType, Model | None]:
        """Select the best provider based on rules and preferences."""
        # Priority 1: Preferred provider
        if preferred_provider:
            try:
                pt = ProviderType(preferred_provider)
                provider = self._resource.get_provider(pt)
                if provider and provider.enabled:
                    model = self._get_model_for_provider(provider, preferred_model)
                    return pt, model
            except ValueError:
                pass
        
        # Priority 2: Matching rule
        if rule and rule.provider:
            provider = self._resource.get_provider(rule.provider)
            if provider and provider.enabled:
                model = self._get_model_for_provider(
                    provider,
                    rule.model or preferred_model,
                )
                return rule.provider, model
        
        # Priority 3: Required capability
        if required_capability:
            models = self._resource.find_models_for_capability(required_capability)
            if models:
                model, provider_type = self._select_best_model_by_cost(models)
                provider = self._resource.get_provider(provider_type)
                return provider_type, model
        
        # Priority 4: Default provider
        default_provider = self._resource.get_provider(self._default_provider)
        if default_provider and default_provider.enabled:
            model = self._get_model_for_provider(default_provider, preferred_model)
            return self._default_provider, model
        
        # Priority 5: Any available provider
        for provider in self._resource.list_providers():
            if provider.enabled:
                model = self._get_model_for_provider(provider, preferred_model)
                return provider.type, model
        
        # Fallback: Ollama (local)
        if self.enable_fallback:
            ollama = self._resource.get_provider(ProviderType.OLLAMA)
            if ollama and ollama.enabled:
                model = self._get_model_for_provider(ollama, None)
                return ProviderType.OLLAMA, model
        
        raise NoProviderAvailableError(
            "No provider available for routing",
            capability=required_capability.value if required_capability else None,
        )

    def _get_model_for_provider(
        self,
        provider: Provider,
        preferred_model: str | None,
    ) -> Model | None:
        """Get the best model for a provider."""
        if not provider.models:
            return None
        
        if preferred_model:
            for model in provider.models:
                if model.id == preferred_model:
                    return model
        
        # Return first available model
        return provider.models[0]

    def _select_best_model_by_cost(
        self,
        models: list[tuple[Model, Provider]],
    ) -> tuple[Model, ProviderType]:
        """Select model based on cost optimization."""
        if not models:
            raise NoProviderAvailableError("No models available")
        
        if not self.cost_optimization:
            # Return highest quality
            return models[0]
        
        # Simple cost-based selection (prefer local models)
        for model, provider_type in models:
            if provider_type == ProviderType.OLLAMA:
                return model, provider_type
        
        # Fall back to first available
        return models[0]

    async def _call_provider(
        self,
        provider_type: ProviderType,
        model: Model | None,
        messages: list[Message],
    ) -> str:
        """Call the selected provider (placeholder)."""
        # This is where actual provider calls would happen
        # For now, return a placeholder
        logger.info(
            "Calling provider",
            provider=provider_type.value,
            model=model.id if model else "unknown",
        )
        
        # TODO (legacy): Implement actual provider calls
        # Note: This is the legacy solvens/router/. 
        # Active implementation uses cosmos/providers/
        return f"Response from {provider_type.value}"

    def _log_routing(
        self,
        content: str,
        provider_type: ProviderType,
        model: Model | None,
        rule: RoutingRule | None,
    ) -> None:
        """Log routing decision for analysis."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "content_preview": content[:100],
            "provider": provider_type.value,
            "model": model.id if model else None,
            "rule": rule.name if rule else None,
        }
        self._routing_history.append(entry)
        
        # Keep only last 1000 entries
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-1000:]

    @property
    def routing_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        return {
            "total_routes": len(self._routing_history),
            "rules_count": len(self._rules),
            "providers_count": len(self._resource.list_providers()),
            "recent_routes": self._routing_history[-10:],
        }
