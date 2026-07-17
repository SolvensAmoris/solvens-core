# SOLVENS CORE - Benchmark Report

**Generated:** 2026-07-17T21:13:27.837563
**Experiment:** quick-benchmark
**Version:** 1.0.0

## Configuration

```yaml
model: gpt-4o-mini
iterations: 3
warmup: 1
timeout: 60s
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
| solvens-core | 3 | 402.22 | 2464 | $0.000000 | 0.06 |

## Statistical Analysis

### solvens-core

| Metric | Mean | Median | Std Dev | P95 | Min | Max |
|--------|------|--------|---------|-----|-----|-----|
| Duration (ms) | 402.22 | 402.20 | 0.06 | 402.28 | 402.18 | 402.29 |
| Tokens | 2464.00 | 2464.00 | 0.00 | 2464.00 | 2464.00 | 2464.00 |
| Memory (MB) | 0.06 | 0.06 | 0.00 | 0.06 | 0.05 | 0.06 |

## Analysis (Impartial)

### Observed Strengths

- Only one framework benchmarked; comparative analysis not available

### Observed Weaknesses

- Comparative weakness analysis requires multiple frameworks

### Identified Bottlenecks

Based on the measured data:

- Highest single run duration: 402.29ms (solvens-core)
- Peak memory usage observed: 0.06MB

### Optimization Opportunities

Potential areas for improvement (based on observed data):

1. **Cache optimization**: Current cache hit rate is low - consider improving cache strategy

## Reproducibility

To reproduce these benchmarks, use the following configuration:

```bash
python -m benchmarks.run --config quick-benchmark
```

Or programmatically:

```python
from benchmarks.config import BenchmarkConfig
config = BenchmarkConfig(
    experiment_name='quick-benchmark',
    iterations=3,
    use_mocks=True,
)
```

## Notes

- All benchmarks used the same configuration for fair comparison
- Mock mode was used for reproducibility
- Results may vary based on system load and network conditions
- 3 total runs executed

---
*This report was generated automatically and reflects objective measurements.*