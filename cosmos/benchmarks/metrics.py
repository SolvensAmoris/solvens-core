"""
Benchmark Metrics for COSMOS

Defines BenchmarkResult dataclass with all required metrics.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class BenchmarkResult:
    """
    Complete benchmark result for a framework run.
    
    All metrics are measured or calculated, not estimated.
    """
    # Framework identification
    framework: str
    
    # Timing
    execution_time_ms: float
    setup_time_ms: float = 0.0
    teardown_time_ms: float = 0.0
    
    # Memory
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    
    # DAG metrics
    dag_nodes_count: int = 0
    dag_edges_count: int = 0
    original_nodes: int = 0
    optimized_nodes: int = 0
    
    # Optimization metrics
    structural_reduction_pct: float = 0.0  # (original - optimized) / original * 100
    parallelism_achieved_pct: float = 0.0   # concurrent_tasks / total_tasks * 100
    subgraph_reuse_pct: float = 0.0         # cached_nodes / total_executions * 100
    
    # Cost metrics
    tokens_consumed: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    
    # Provider breakdown
    provider_costs: dict[str, float] = field(default_factory=dict)
    provider_tokens: dict[str, int] = field(default_factory=dict)
    
    # Errors
    error_count: int = 0
    retry_count: int = 0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    workflow_name: str = ""
    description: str = ""
    
    @property
    def total_cost_usd(self) -> float:
        """Total cost including all providers."""
        return sum(self.provider_costs.values()) if self.provider_costs else self.cost_usd
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "framework": self.framework,
            "workflow": self.workflow_name,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "dag_nodes": self.dag_nodes_count,
            "structural_reduction_pct": round(self.structural_reduction_pct, 1),
            "parallelism_achieved_pct": round(self.parallelism_achieved_pct, 1),
            "subgraph_reuse_pct": round(self.subgraph_reuse_pct, 1),
            "tokens_consumed": self.tokens_consumed,
            "cost_usd": round(self.cost_usd, 4),
        }
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"{self.framework} ({self.workflow_name}):\n"
            f"  Time: {self.execution_time_ms:.0f}ms\n"
            f"  Memory: {self.peak_memory_mb:.1f}MB\n"
            f"  DAG: {self.dag_nodes_count} nodes\n"
            f"  Reduction: {self.structural_reduction_pct:.1f}%\n"
            f"  Parallelism: {self.parallelism_achieved_pct:.1f}%\n"
            f"  Reuse: {self.subgraph_reuse_pct:.1f}%\n"
            f"  Tokens: {self.tokens_consumed:,}\n"
            f"  Cost: ${self.cost_usd:.4f}"
        )


# Provider pricing (2026 rates in USD per 1M tokens)
PROVIDER_PRICING = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    },
    "anthropic": {
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    },
    "google": {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    },
    "deepseek": {
        "deepseek-chat": {"input": 0.14, "output": 0.28},
    },
    "ollama": {
        "llama3": {"input": 0.0, "output": 0.0},  # Free when local
        "mixtral": {"input": 0.0, "output": 0.0},
    },
}


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost in USD for a provider/model/token combination.
    
    Args:
        provider: Provider name (e.g., "openai", "anthropic")
        model: Model name (e.g., "gpt-4o")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    
    Returns:
        Cost in USD
    """
    provider_pricing = PROVIDER_PRICING.get(provider, {})
    model_pricing = provider_pricing.get(model, {"input": 0, "output": 0})
    
    input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
    
    return input_cost + output_cost
