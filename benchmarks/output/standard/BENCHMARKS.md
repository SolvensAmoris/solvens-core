# SOLVENS CORE - Benchmark Report

**Generated:** 2026-07-17T21:13:45.738766
**Experiment:** standard-benchmark
**Version:** 1.0.0

## Configuration

```yaml
model: gpt-4o-mini
iterations: 10
warmup: 2
timeout: 300s
mock_mode: True
mock_latency: 100.0ms

python_version: 3.13.14
platform: Linux-6.8.0-1051-gke-x86_64-with-glibc2.41
cpu_count: 4
total_memory_gb: 15.615692138671875
```

## Raw Results

### Summary by Framework

| Framework | Runs | Avg Duration (ms) | Avg Tokens | Avg Cost | Avg Memory (MB) |
|-----------|------|------------------|-----------|---------|-----------------|
| solvens-core | 10 | 603.33 | 3696 | $0.000000 | 0.06 |

## Statistical Analysis

### solvens-core

| Metric | Mean | Median | Std Dev | P95 | Min | Max |
|--------|------|--------|---------|-----|-----|-----|
| Duration (ms) | 603.33 | 603.30 | 0.11 | 603.50 | 603.20 | 603.54 |
| Tokens | 3696.00 | 3696.00 | 0.00 | 3696.00 | 3696.00 | 3696.00 |
| Memory (MB) | 0.06 | 0.06 | 0.00 | 0.06 | 0.06 | 0.06 |

## Analysis (Impartial)

### Observed Strengths

- Only one framework benchmarked; comparative analysis not available

### Observed Weaknesses

- Comparative weakness analysis requires multiple frameworks

### Identified Bottlenecks

Based on the measured data:

- Highest single run duration: 603.54ms (solvens-core)
- Peak memory usage observed: 0.06MB

### Optimization Opportunities

Potential areas for improvement (based on observed data):

1. **Cache optimization**: Current cache hit rate is low - consider improving cache strategy

## Reproducibility

To reproduce these benchmarks, use the following configuration:

```bash
python -m benchmarks.run --config standard-benchmark
```

Or programmatically:

```python
from benchmarks.config import BenchmarkConfig
config = BenchmarkConfig(
    experiment_name='standard-benchmark',
    iterations=10,
    use_mocks=True,
)
```

## Notes

- All benchmarks used the same configuration for fair comparison
- Mock mode was used for reproducibility
- Results may vary based on system load and network conditions
- 10 total runs executed

---
*This report was generated automatically and reflects objective measurements.*