# SOLVENS CORE - Benchmark Suite

Reproducible benchmarks for measuring SOLVENS CORE performance.

## Overview

This benchmark suite provides objective, reproducible measurements of SOLVENS CORE performance. All benchmarks use the same configuration for fair comparison.

## Quick Start

```bash
# Run quick benchmarks (3 iterations)
python -m benchmarks.run --config quick

# Run standard benchmarks (10 iterations)
python -m benchmarks.run --config standard

# Run extended benchmarks (30 iterations)
python -m benchmarks.run --config extended
```

## Configuration

Three benchmark configurations are available:

| Config | Iterations | Warmup | DAG Nodes | Description |
|--------|------------|--------|-----------|-------------|
| `quick` | 3 | 1 | 3 | Fast sanity check |
| `standard` | 10 | 2 | 5 | Standard benchmark |
| `extended` | 30 | 5 | 10 | Comprehensive analysis |

## Output Files

Benchmarks generate the following files in `benchmarks/output/{config}/`:

| File | Description |
|------|-------------|
| `RESULTS.json` | Complete results in JSON format |
| `RESULTS.csv` | Results in CSV format for spreadsheet analysis |
| `BENCHMARKS.md` | Human-readable report with statistical analysis |
| `graphs/` | (Future) Visualization graphs |

## Metrics Collected

### Timing
- Total duration (wall clock)
- Duration per node
- Percentiles (P50, P95, P99)

### Resource Usage
- Peak memory (MB)
- CPU usage (average and max)

### Token Usage
- Input tokens
- Output tokens
- Total tokens
- Throughput (tokens/second)

### Cost
- Estimated cost (when using real API)
- Cost per run

### Caching
- Cache hit rate
- Cache hits / misses

## Statistical Analysis

Each report includes:
- Mean, median, standard deviation
- Min, max values
- Percentiles (P50, P75, P90, P95, P99)
- 95% confidence intervals

## Impartial Analysis

The benchmark reports include **objective analysis** that:
- Identifies actual strengths (no assumptions)
- Documents observed weaknesses
- Proposes optimizations based on data

**Important:** No metrics are set as "goals" - all measurements are objective.

## Reproducibility

To reproduce benchmarks exactly:

```python
from benchmarks.config import BenchmarkConfig

config = BenchmarkConfig(
    experiment_name="my-experiment",
    iterations=10,
    use_mocks=True,
    mock_latency_ms=100.0,
)
```

## Adding New Benchmarks

To add a new benchmark framework:

```python
from benchmarks.metrics import MetricsCollector, NodeExecution

def benchmark_my_framework():
    with MetricsCollector("my-framework", "workflow-name", "run-id") as collector:
        # Run your benchmark
        # ...
        node_exec = NodeExecution(
            node_id="node-1",
            node_type="task",
            start_time=start,
            end_time=end,
            duration_ms=duration * 1000,
            input_tokens=100,
            output_tokens=200,
        )
        collector.add_node(node_exec)
```

## Notes

- All benchmarks use **mock mode** by default for reproducibility
- Real API benchmarks require valid API keys
- Results may vary based on system load
- Memory measurements include Python interpreter overhead

## License

Part of SOLVENS CORE - Apache 2.0
