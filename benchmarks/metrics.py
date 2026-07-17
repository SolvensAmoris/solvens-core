"""
Benchmark Metrics Collection and Analysis

Provides objective measurement of performance characteristics.
"""

import time
import tracemalloc
import psutil
import os
import statistics
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ExecutionStatus(Enum):
    """Status of a benchmark execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class NodeExecution:
    """Single node execution record."""
    node_id: str
    node_type: str  # agent, task, provider
    start_time: float
    end_time: float
    duration_ms: float
    
    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    
    # Caching
    cached: bool = False
    cache_hit: bool = False
    
    # Provider info
    provider: str = "mock"
    model: str = "mock"
    
    # Cost (if applicable)
    cost_usd: float = 0.0
    
    # Memory delta for this node
    memory_delta_mb: float = 0.0


@dataclass
class RunMetrics:
    """Complete metrics for a single benchmark run."""
    run_id: str
    framework: str
    workflow_name: str
    status: ExecutionStatus
    
    # Timing
    total_duration_ms: float
    wall_clock_time_ms: float
    
    # Node executions
    nodes: list[NodeExecution] = field(default_factory=list)
    
    # Memory
    peak_memory_mb: float = 0.0
    memory_at_start_mb: float = 0.0
    memory_at_end_mb: float = 0.0
    
    # CPU
    cpu_percent_avg: float = 0.0
    cpu_percent_max: float = 0.0
    
    # Token summary
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    
    # Cost
    total_cost_usd: float = 0.0
    
    # Cache statistics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    
    # DAG metrics
    dag_nodes: int = 0
    dag_edges: int = 0
    parallel_executions: int = 0
    
    # Errors
    error_message: Optional[str] = None
    
    # Throughput
    throughput_tokens_per_second: float = 0.0
    nodes_per_second: float = 0.0
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics after collection."""
        if self.nodes:
            self.total_input_tokens = sum(n.input_tokens for n in self.nodes)
            self.total_output_tokens = sum(n.output_tokens for n in self.nodes)
            self.total_tokens = self.total_input_tokens + self.total_output_tokens
            
            self.cache_hits = sum(1 for n in self.nodes if n.cache_hit)
            self.cache_misses = sum(1 for n in self.nodes if not n.cached or not n.cache_hit)
            total_cacheable = self.cache_hits + self.cache_misses
            self.cache_hit_rate = self.cache_hits / total_cacheable if total_cacheable > 0 else 0.0
            
            self.total_cost_usd = sum(n.cost_usd for n in self.nodes)
            
            if self.total_duration_ms > 0:
                self.throughput_tokens_per_second = self.total_tokens / (self.total_duration_ms / 1000)
                self.nodes_per_second = len(self.nodes) / (self.total_duration_ms / 1000)


@dataclass
class StatisticalSummary:
    """Statistical summary across multiple runs."""
    metric_name: str
    framework: str
    workflow: str
    
    # Basic statistics
    count: int
    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    
    # Percentiles
    p50: float  # Median
    p75: float
    p90: float
    p95: float
    p99: float
    
    # Confidence interval (95%)
    ci_lower: float
    ci_upper: float
    
    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "framework": self.framework,
            "workflow": self.workflow,
            "count": self.count,
            "mean": round(self.mean, 4),
            "median": round(self.median, 4),
            "std_dev": round(self.std_dev, 4),
            "min": round(self.min_val, 4),
            "max": round(self.max_val, 4),
            "p50": round(self.p50, 4),
            "p75": round(self.p75, 4),
            "p90": round(self.p90, 4),
            "p95": round(self.p95, 4),
            "p99": round(self.p99, 4),
            "ci_95_lower": round(self.ci_lower, 4),
            "ci_95_upper": round(self.ci_upper, 4),
        }


def calculate_percentile(data: list[float], p: float) -> float:
    """Calculate percentile from sorted data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * p / 100
    floor = int(index)
    ceil = min(floor + 1, len(sorted_data) - 1)
    return sorted_data[floor] * (ceil - index) + sorted_data[ceil] * (index - floor)


def calculate_statistics(values: list[float], framework: str, workflow: str, metric_name: str) -> StatisticalSummary:
    """Calculate statistical summary for a set of values."""
    if len(values) < 2:
        # Not enough data for statistics
        return StatisticalSummary(
            metric_name=metric_name,
            framework=framework,
            workflow=workflow,
            count=len(values),
            mean=values[0] if values else 0.0,
            median=values[0] if values else 0.0,
            std_dev=0.0,
            min_val=values[0] if values else 0.0,
            max_val=values[0] if values else 0.0,
            p50=values[0] if values else 0.0,
            p75=values[0] if values else 0.0,
            p90=values[0] if values else 0.0,
            p95=values[0] if values else 0.0,
            p99=values[0] if values else 0.0,
            ci_lower=values[0] if values else 0.0,
            ci_upper=values[0] if values else 0.0,
        )
    
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)
    median = statistics.median(values)
    
    # Calculate confidence interval (95%)
    ci_margin = 1.96 * (std_dev / (len(values) ** 0.5))
    
    return StatisticalSummary(
        metric_name=metric_name,
        framework=framework,
        workflow=workflow,
        count=len(values),
        mean=mean,
        median=median,
        std_dev=std_dev,
        min_val=min(values),
        max_val=max(values),
        p50=calculate_percentile(values, 50),
        p75=calculate_percentile(values, 75),
        p90=calculate_percentile(values, 90),
        p95=calculate_percentile(values, 95),
        p99=calculate_percentile(values, 99),
        ci_lower=mean - ci_margin,
        ci_upper=mean + ci_margin,
    )


class MetricsCollector:
    """Context manager for collecting run metrics."""
    
    def __init__(self, framework: str, workflow_name: str, run_id: str):
        self.framework = framework
        self.workflow_name = workflow_name
        self.run_id = run_id
        self.metrics: Optional[RunMetrics] = None
        self._start_time: float = 0
        self._process = psutil.Process(os.getpid())
        self._nodes: list[NodeExecution] = []
        self._cpu_samples: list[float] = []
        self._memory_start: float = 0
        self._peak_memory: float = 0
    
    def __enter__(self):
        self._start_time = time.perf_counter()
        self._memory_start = self._process.memory_info().rss / (1024 * 1024)
        tracemalloc.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        wall_time = (end_time - self._start_time) * 1000
        
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_end = self._process.memory_info().rss / (1024 * 1024)
        
        self.metrics = RunMetrics(
            run_id=self.run_id,
            framework=self.framework,
            workflow_name=self.workflow_name,
            status=ExecutionStatus.SUCCESS if exc_type is None else ExecutionStatus.ERROR,
            total_duration_ms=wall_time,
            wall_clock_time_ms=wall_time,
            nodes=self._nodes,
            peak_memory_mb=peak_mem / (1024 * 1024),
            memory_at_start_mb=self._memory_start,
            memory_at_end_mb=memory_end,
            cpu_percent_avg=statistics.mean(self._cpu_samples) if self._cpu_samples else 0,
            cpu_percent_max=max(self._cpu_samples) if self._cpu_samples else 0,
            error_message=str(exc_val) if exc_val else None,
        )
        self.metrics.calculate_derived_metrics()
        return False
    
    def add_node(self, node: NodeExecution):
        """Add a node execution."""
        self._nodes.append(node)
    
    def sample_cpu(self):
        """Sample CPU usage."""
        try:
            self._cpu_samples.append(self._process.cpu_percent())
        except:
            pass
