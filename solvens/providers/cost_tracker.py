"""
cost_tracker.py - Real-time Cost Tracking for Multi-Provider
==========================================================

Track costs per provider, model, and operation in real-time.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import threading
import time


class Provider(Enum):
    """Supported providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    GROK = "grok"
    DEEPSEEK = "deepseek"


@dataclass
class ModelPricing:
    """Pricing per model per 1K tokens."""
    
    # OpenAI
    GPT4_TURBO_INPUT: float = 0.01
    GPT4_TURBO_OUTPUT: float = 0.03
    GPT35_TURBO_INPUT: float = 0.0005
    GPT35_TURBO_OUTPUT: float = 0.0015
    
    # Anthropic
    CLAUDE3_OPUS_INPUT: float = 0.015
    CLAUDE3_OPUS_OUTPUT: float = 0.075
    CLAUDE3_SONNET_INPUT: float = 0.003
    CLAUDE3_SONNET_OUTPUT: float = 0.015
    CLAUDE3_HAIKU_INPUT: float = 0.00025
    CLAUDE3_HAIKU_OUTPUT: float = 0.00125
    
    # Google
    GEMINI_PRO_INPUT: float = 0.00125
    GEMINI_PRO_OUTPUT: float = 0.00375
    
    # Ollama (local - free)
    OLLAMA_INPUT: float = 0.0
    OLLAMA_OUTPUT: float = 0.0
    
    # Grok
    GROK_INPUT: float = 0.005
    GROK_OUTPUT: float = 0.015
    
    # DeepSeek
    DEEPSEEK_CODER_INPUT: float = 0.0014
    DEEPSEEK_CODER_OUTPUT: float = 0.0028
    
    def get_price(self, model: str, is_output: bool = False) -> float:
        """Get price per 1K tokens for model."""
        model_lower = model.lower()
        
        if "gpt-4-turbo" in model_lower:
            return self.GPT4_TURBO_OUTPUT if is_output else self.GPT4_TURBO_INPUT
        elif "gpt-3.5-turbo" in model_lower:
            return self.GPT35_TURBO_OUTPUT if is_output else self.GPT35_TURBO_INPUT
        
        elif "claude-3-opus" in model_lower:
            return self.CLAUDE3_OPUS_OUTPUT if is_output else self.CLAUDE3_OPUS_INPUT
        elif "claude-3-sonnet" in model_lower:
            return self.CLAUDE3_SONNET_OUTPUT if is_output else self.CLAUDE3_SONNET_INPUT
        elif "claude-3-haiku" in model_lower or "claude-3.5-haiku" in model_lower:
            return self.CLAUDE3_HAIKU_OUTPUT if is_output else self.CLAUDE3_HAIKU_INPUT
        
        elif "gemini" in model_lower:
            return self.GEMINI_PRO_OUTPUT if is_output else self.GEMINI_PRO_INPUT
        
        elif "ollama" in model_lower or "llama" in model_lower or "mistral" in model_lower:
            return self.OLLAMA_OUTPUT if is_output else self.OLLAMA_INPUT
        
        elif "grok" in model_lower:
            return self.GROK_OUTPUT if is_output else self.GROK_INPUT
        
        elif "deepseek" in model_lower:
            return self.DEEPSEEK_CODER_OUTPUT if is_output else self.DEEPSEEK_CODER_INPUT
        
        # Default unknown model pricing
        return 0.01


@dataclass
class CostEntry:
    """Single cost entry."""
    timestamp: datetime
    provider: Provider
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    operation: str = "chat"
    request_id: Optional[str] = None


@dataclass
class ProviderStats:
    """Statistics for a provider."""
    provider: Provider
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: float = 0.0
    
    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


class CostTracker:
    """
    Real-time cost tracker for multi-provider operations.
    
    Usage:
        tracker = CostTracker()
        
        # Start tracking
        tracker.start_request("openai", "gpt-4-turbo", request_id="req_123")
        
        # ... make API call ...
        
        # End tracking
        tracker.end_request(
            request_id="req_123",
            input_tokens=1000,
            output_tokens=500
        )
        
        # Get stats
        stats = tracker.get_stats()
        budget = tracker.check_budget(limit=10.0)
    """
    
    def __init__(self, budget_limit: Optional[float] = None):
        self._lock = threading.Lock()
        self._entries: List[CostEntry] = []
        self._provider_stats: Dict[Provider, ProviderStats] = {
            p: ProviderStats(provider=p) for p in Provider
        }
        self._active_requests: Dict[str, datetime] = {}
        self._pricing = ModelPricing()
        self._budget_limit = budget_limit
        self._budget_spent: float = 0.0
    
    def start_request(
        self,
        provider: str,
        model: str,
        operation: str = "chat",
        request_id: Optional[str] = None
    ) -> str:
        """Start tracking a request."""
        request_id = request_id or f"req_{int(time.time() * 1000)}"
        
        with self._lock:
            self._active_requests[request_id] = datetime.now()
        
        return request_id
    
    def end_request(
        self,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        operation: Optional[str] = None
    ) -> float:
        """
        End tracking a request and calculate cost.
        
        Returns:
            Cost of the request
        """
        with self._lock:
            if request_id not in self._active_requests:
                return 0.0
            
            start_time = self._active_requests.pop(request_id)
            
            # Calculate cost
            input_price = self._pricing.get_price(model or "unknown", is_output=False)
            output_price = self._pricing.get_price(model or "unknown", is_output=True)
            
            input_cost = (input_tokens / 1000) * input_price
            output_cost = (output_tokens / 1000) * output_price
            total_cost = input_cost + output_cost
            
            # Create entry
            entry = CostEntry(
                timestamp=start_time,
                provider=Provider(provider or "openai"),
                model=model or "unknown",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=total_cost,
                operation=operation or "chat",
                request_id=request_id
            )
            self._entries.append(entry)
            
            # Update stats
            stats = self._provider_stats.get(Provider(provider or "openai"))
            if stats:
                stats.total_requests += 1
                stats.total_input_tokens += input_tokens
                stats.total_output_tokens += output_tokens
                stats.total_cost += total_cost
                stats.latency_ms += (datetime.now() - start_time).total_seconds() * 1000
            
            # Update budget
            self._budget_spent += total_cost
            
            return total_cost
    
    def get_stats(self) -> Dict[str, ProviderStats]:
        """Get statistics per provider."""
        with self._lock:
            return dict(self._provider_stats)
    
    def get_total_cost(self) -> float:
        """Get total cost across all providers."""
        with self._lock:
            return sum(e.cost for e in self._entries)
    
    def get_total_tokens(self) -> Tuple[int, int]:
        """Get total input and output tokens."""
        with self._lock:
            input_total = sum(e.input_tokens for e in self._entries)
            output_total = sum(e.output_tokens for e in self._entries)
            return input_total, output_total
    
    def get_recent_entries(self, limit: int = 10) -> List[CostEntry]:
        """Get most recent cost entries."""
        with self._lock:
            return sorted(self._entries, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def check_budget(self, limit: Optional[float] = None) -> Dict:
        """
        Check budget status.
        
        Returns:
            Dict with budget status
        """
        limit = limit or self._budget_limit or float('inf')
        
        with self._lock:
            spent = self._budget_spent
            remaining = max(0, limit - spent)
            percent = (spent / limit * 100) if limit < float('inf') else 0
            
            return {
                "limit": limit,
                "spent": spent,
                "remaining": remaining,
                "percent_used": percent,
                "over_budget": spent > limit,
                "entries_count": len(self._entries)
            }
    
    def reset(self):
        """Reset all tracking."""
        with self._lock:
            self._entries.clear()
            self._active_requests.clear()
            self._budget_spent = 0.0
            
            for stats in self._provider_stats.values():
                stats.total_requests = 0
                stats.total_input_tokens = 0
                stats.total_output_tokens = 0
                stats.total_cost = 0.0
                stats.latency_ms = 0.0


# ============================================================
# Streaming Cost Tracker
# ============================================================

class StreamingCostTracker(CostTracker):
    """
    Cost tracker with streaming support.
    
    Tracks costs in real-time as tokens are generated.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._streaming_tokens: Dict[str, int] = {}
    
    def start_stream(
        self,
        provider: str,
        model: str,
        request_id: Optional[str] = None
    ) -> str:
        """Start streaming cost tracking."""
        request_id = self.start_request(provider, model, operation="stream", request_id=request_id)
        self._streaming_tokens[request_id] = 0
        return request_id
    
    def add_output_token(
        self,
        request_id: str,
        model: Optional[str] = None
    ) -> float:
        """Add a single output token and update cost."""
        with self._lock:
            if request_id in self._streaming_tokens:
                self._streaming_tokens[request_id] += 1
        
        # This is called per-token, so we batch the cost update
        # The actual cost calculation happens at end_stream
        return 0.0  # Cost will be calculated at end_stream
    
    def end_stream(
        self,
        request_id: str,
        input_tokens: int,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> float:
        """End streaming and calculate final cost."""
        with self._lock:
            output_tokens = self._streaming_tokens.pop(request_id, 0)
        
        return self.end_request(
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            provider=provider,
            operation="stream"
        )


# ============================================================
# Formatters
# ============================================================

def format_cost(cost: float) -> str:
    """Format cost as currency string."""
    if cost < 0.001:
        return f"${cost * 1000:.2f}m"  # millicents
    elif cost < 1:
        return f"${cost * 1000:.2f}¢"
    else:
        return f"${cost:.4f}"


def format_tokens(tokens: int) -> str:
    """Format token count."""
    if tokens < 1000:
        return f"{tokens}"
    elif tokens < 1000000:
        return f"{tokens / 1000:.1f}K"
    else:
        return f"{tokens / 1000000:.1f}M"


def format_stats(stats: Dict[str, ProviderStats]) -> str:
    """Format provider stats as string."""
    lines = ["┌" + "─" * 70 + "┐"]
    lines.append("│" + " PROVIDER COST SUMMARY ".center(70) + "│")
    lines.append("├" + "─" * 70 + "┤")
    lines.append("│" + f" {'Provider':<15} {'Requests':>10} {'Input':>10} {'Output':>10} {'Cost':>12} │".format(
        "Provider", "Requests", "Input", "Output", "Cost"
    ))
    lines.append("├" + "─" * 70 + "┤")
    
    total_cost = 0
    total_requests = 0
    total_tokens = 0
    
    for provider, stat in sorted(stats.items(), key=lambda x: x[1].total_cost, reverse=True):
        if stat.total_requests > 0:
            cost_str = format_cost(stat.total_cost)
            lines.append("│" + f" {provider.value:<15} {stat.total_requests:>10} {format_tokens(stat.total_input_tokens):>10} {format_tokens(stat.total_output_tokens):>10} {cost_str:>12} │")
            total_cost += stat.total_cost
            total_requests += stat.total_requests
            total_tokens += stat.total_tokens
    
    lines.append("├" + "─" * 70 + "┤")
    lines.append("│" + f" {'TOTAL':<15} {total_requests:>10} {'':<10} {'':<10} {format_cost(total_cost):>12} │")
    lines.append("└" + "─" * 70 + "┘")
    
    return '\n'.join(lines)


# ============================================================
# Demo
# ============================================================

def demo():
    """Demo del cost tracker."""
    print("=" * 60)
    print("COST TRACKER DEMO")
    print("=" * 60)
    
    tracker = CostTracker(budget_limit=10.0)
    
    # Simular requests
    print("\n[Simulating API calls...]")
    
    # GPT-4 request
    req1 = tracker.start_request("openai", "gpt-4-turbo", request_id="req_001")
    time.sleep(0.1)
    cost1 = tracker.end_request(req1, input_tokens=1500, output_tokens=800, provider="openai", model="gpt-4-turbo")
    print(f"  GPT-4 Turbo: {format_cost(cost1)}")
    
    # Claude request
    req2 = tracker.start_request("anthropic", "claude-3-sonnet", request_id="req_002")
    time.sleep(0.1)
    cost2 = tracker.end_request(req2, input_tokens=2000, output_tokens=1000, provider="anthropic", model="claude-3-sonnet")
    print(f"  Claude 3 Sonnet: {format_cost(cost2)}")
    
    # Ollama (free)
    req3 = tracker.start_request("ollama", "llama3", request_id="req_003")
    time.sleep(0.1)
    cost3 = tracker.end_request(req3, input_tokens=1000, output_tokens=500, provider="ollama", model="llama3")
    print(f"  Ollama (local): {format_cost(cost3)}")
    
    # Mostrar stats
    print("\n" + format_stats(tracker.get_stats()))
    
    # Budget check
    budget = tracker.check_budget()
    print(f"\nBudget Status: {budget['percent_used']:.1f}% used (${budget['spent']:.4f} / ${budget['limit']:.2f})")
    
    if budget['over_budget']:
        print("⚠️  OVER BUDGET!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
