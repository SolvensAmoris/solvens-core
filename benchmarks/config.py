"""
Benchmark Configuration for SOLVENS CORE

This module defines the reproducible benchmark configuration.
All experiments use the same settings for fair comparison.
"""

from dataclasses import dataclass, field
from typing import Optional
import platform
import os


@dataclass
class BenchmarkConfig:
    """Complete configuration for benchmark reproducibility."""
    
    # Experiment metadata
    experiment_name: str = "solvens-core-benchmark"
    experiment_version: str = "1.0.0"
    date: str = ""  # Set at runtime
    
    # System configuration
    python_version: str = ""
    platform: str = ""
    cpu_count: int = 0
    total_memory_gb: float = 0.0
    
    # Model configuration (same for all frameworks)
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int = 2048
    
    # Benchmark settings
    iterations: int = 10
    warmup_iterations: int = 2
    timeout_seconds: int = 300
    
    # Workflow configuration
    workflow_complexity: str = "medium"  # simple, medium, complex
    dag_nodes: int = 5
    
    # Mock settings (for reproducibility without API calls)
    use_mocks: bool = True
    mock_latency_ms: float = 100.0
    mock_tokens_per_second: float = 100.0
    
    def __post_init__(self):
        import datetime
        self.date = datetime.datetime.now().isoformat()
        self.python_version = platform.python_version()
        self.platform = platform.platform()
        self.cpu_count = os.cpu_count() or 1
        
        # Estimate memory (this is approximate)
        try:
            import psutil
            self.total_memory_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            self.total_memory_gb = 0.0
    
    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return {
            "experiment_name": self.experiment_name,
            "experiment_version": self.experiment_version,
            "date": self.date,
            "python_version": self.python_version,
            "platform": self.platform,
            "cpu_count": self.cpu_count,
            "total_memory_gb": round(self.total_memory_gb, 2),
            "model": self.model,
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "iterations": self.iterations,
            "warmup_iterations": self.warmup_iterations,
            "timeout_seconds": self.timeout_seconds,
            "workflow_complexity": self.workflow_complexity,
            "dag_nodes": self.dag_nodes,
            "use_mocks": self.use_mocks,
            "mock_latency_ms": self.mock_latency_ms,
            "mock_tokens_per_second": self.mock_tokens_per_second,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkConfig":
        """Load configuration from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


# Standard benchmark configurations
BENCHMARK_CONFIGS = {
    "quick": BenchmarkConfig(
        experiment_name="quick-benchmark",
        iterations=3,
        warmup_iterations=1,
        timeout_seconds=60,
        workflow_complexity="simple",
        dag_nodes=3,
    ),
    "standard": BenchmarkConfig(
        experiment_name="standard-benchmark",
        iterations=10,
        warmup_iterations=2,
        timeout_seconds=300,
        workflow_complexity="medium",
        dag_nodes=5,
    ),
    "extended": BenchmarkConfig(
        experiment_name="extended-benchmark",
        iterations=30,
        warmup_iterations=5,
        timeout_seconds=600,
        workflow_complexity="complex",
        dag_nodes=10,
    ),
}
