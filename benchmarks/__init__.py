"""
SOLVENS CORE - Benchmark Suite

Provides reproducible benchmarking for SOLVENS CORE and comparison frameworks.
"""

from benchmarks.config import BenchmarkConfig, BENCHMARK_CONFIGS
from benchmarks.metrics import (
    RunMetrics,
    NodeExecution,
    MetricsCollector,
    StatisticalSummary,
    calculate_statistics,
)
from benchmarks.reporter import BenchmarkReporter
from benchmarks.run import run_benchmarks, SolvensBenchmark

__all__ = [
    "BenchmarkConfig",
    "BENCHMARK_CONFIGS",
    "RunMetrics",
    "NodeExecution",
    "MetricsCollector",
    "StatisticalSummary",
    "calculate_statistics",
    "BenchmarkReporter",
    "run_benchmarks",
    "SolvensBenchmark",
]
