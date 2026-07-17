# SOLVENS CORE - Scientific Benchmarks

**Version:** 1.0.0  
**Author:** Luis Alberto Burciaga Miker  
**Date:** 2025-01-17

---

## Overview

This document describes the scientific benchmark methodology used to evaluate SOLVENS CORE performance. Benchmarks are designed to be **reproducible**, **objective**, and **comparable** across frameworks.

---

## ⚠️ IMPORTANT: Mock vs Real Benchmarks

### Current Status: PHASE 2.0 COMPLETE (Mock Mode)

The benchmarks described here are currently in **mock mode**. Results shown are simulations, not real API calls.

### Real Benchmarks: PHASE 2.1 (Planned)

Real benchmarks require:
1. API keys configured
2. Calibration phase (50 runs) to validate instrumentation
3. Cost verification against actual API bills
4. Full production runs (3000+ runs)

**DO NOT** present mock results as scientific evidence.

---

## Philosophy

> **Measure, don't assume.**

We believe in:
- **Reproducibility**: Same task, same configuration, same result
- **Objectivity**: No cherry-picking of favorable metrics
- **Transparency**: Full data available in JSON/CSV formats
- **Fairness**: Same conditions for all frameworks

---

## What We Are NOT Measuring

### ❌ Model Intelligence

This benchmark does NOT evaluate:
- Quality of model responses
- Reasoning capabilities
- Knowledge accuracy
- Creative output quality

### ✅ Orchestration Efficiency

This benchmark DOES evaluate:
- Framework overhead
- Latency introduced by orchestration
- Token efficiency (not calling more than needed)
- Cost per task
- Concurrent execution efficiency

> **"This benchmark evaluates orchestration efficiency, not model intelligence."**

All frameworks use the same model (gpt-4o-mini) to isolate framework performance.

---

## Benchmark Framework

### Scientific Benchmark System

The benchmark system is located in `benchmarks/scientific.py`:

```bash
# Run SOLVENS benchmarks
python benchmarks/scientific.py

# Generate visualizations
python benchmarks/plot_generator.py
```

### Output Structure

```
benchmarks/scientific_output/
├── json/
│   └── results.json          # Raw data
├── csv/
│   └── results.csv           # Spreadsheet-ready
├── plots/
│   ├── dashboard.png         # Summary visualization
│   ├── mean_comparison.png   # Mean time comparison
│   ├── heatmap.png           # Framework x Task heatmap
│   ├── percentiles.png        # P50/P95/P99 analysis
│   ├── distribution.png       # Violin plot
│   ├── boxplot.png           # Box plot
│   └── success_rate.png      # Success rates
└── reports/
    └── BENCHMARKS.md         # This document
```

---

## Standardized Tasks

Benchmarks use 8 standardized tasks:

| Task | Description | Complexity | Planning | Memory |
|------|-------------|------------|----------|--------|
| Code Generation | Write Python function with requirements | Medium | Yes | No |
| Data Analysis | Calculate statistics from data | Medium | Yes | No |
| Research Synthesis | Summarize information from multiple sources | High | No | Yes |
| Text Summarization | Summarize text in 3 sentences | Low | No | No |
| Question Answering | Answer based on context | Low | No | No |
| Agent Coordination | Coordinate multiple agents | High | Yes | No |
| Parallel Executor | Execute independent tasks in parallel | Low | No | No |
| Sequential Workflow | Execute tasks with dependencies | Low | Yes | No |

---

## Metrics Collected

### Timing Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `mean_ms` | Arithmetic mean | ms |
| `median_ms` | Median (P50) | ms |
| `std_dev_ms` | Standard deviation | ms |
| `min_ms` | Minimum | ms |
| `max_ms` | Maximum | ms |
| `p50_ms` | 50th percentile | ms |
| `p95_ms` | 95th percentile | ms |
| `p99_ms` | 99th percentile | ms |
| `total_duration_ms` | Total wall time | ms |

### Quality Metrics

| Metric | Description |
|--------|-------------|
| `success` | All iterations completed successfully |
| `output_length` | Average output length in characters |

### System Metrics

| Metric | Description |
|--------|-------------|
| `python_version` | Python version |
| `platform` | Operating system |
| `peak_memory_mb` | Peak memory usage (if available) |
| `avg_cpu_percent` | Average CPU usage (if available) |

---

## Statistical Analysis

### Coefficient of Variation (CV)

Measures consistency of results:

```
CV = (Standard Deviation / Mean) × 100
```

| CV Range | Interpretation |
|----------|----------------|
| < 10% | Highly consistent |
| 10-25% | Moderate consistency |
| 25-50% | High variability |
| > 50% | Very high variability |

### Percentiles

- **P50 (Median)**: 50% of requests complete faster
- **P95**: 95% of requests complete faster (SLA threshold)
- **P99**: 99% of requests complete faster (Critical threshold)

---

## Reproducibility

### Configuration

All benchmarks use identical configuration:

```python
{
    "model": "gpt-4o-mini",
    "provider": "openai",
    "temperature": 0.7,
    "max_tokens": 2048,
    "iterations": 10,
    "warmup_iterations": 2,
}
```

### Version Control

Each benchmark run captures:
- Timestamp
- Framework version
- Python version
- Platform/OS
- Task hash (for verification)

---

## Current Results

### ⚠️ MOCK RESULTS - NOT SCIENTIFIC EVIDENCE

The following results are from **mock mode** (simulations), not real API calls:

### SOLVENS CORE v0.5.1-rc1 (Mock)

| Task | Mean (ms) | P95 (ms) | Success |
|------|-----------|----------|---------|
| Code Generation | 50.15 | 50.17 | ✅ |
| Data Analysis | 50.16 | 50.17 | ✅ |
| Research Synthesis | 50.14 | 50.15 | ✅ |
| Text Summarization | 50.15 | 50.17 | ✅ |
| Question Answering | 50.14 | 50.17 | ✅ |
| Agent Coordination | 50.14 | 50.17 | ✅ |
| Parallel Executor | 50.15 | 50.16 | ✅ |
| Sequential Workflow | 50.14 | 50.16 | ✅ |

### Mock Summary Statistics

- **Total Tasks:** 8
- **Mean Execution Time:** 50.15 ms
- **Coefficient of Variation:** 0.01%
- **Consistency:** High
- **Success Rate:** 100%

**These numbers are for framework validation only. Real benchmarks will produce different values.**

---

## Hypotheses (Not Results)

The following are **research hypotheses**, not guaranteed outcomes:

| Metric | Hypothesis | Status |
|--------|------------|--------|
| SOLVENS cost per task | < $0.0025 | 🔬 Testing |
| SOLVENS P99 latency | < 2500ms | 🔬 Testing |
| SOLVENS success rate | > 99% | 🔬 Testing |
| SOLVENS vs LangGraph | Competitive | 🔬 Testing |
| SOLVENS vs AutoGen | Competitive | 🔬 Testing |

---

## Visualization Examples

### Generated Plots

1. **Dashboard** (`dashboard.png`) - Summary of all metrics
2. **Mean Comparison** (`mean_comparison.png`) - Bar chart comparison
3. **Heatmap** (`heatmap.png`) - Framework × Task matrix
4. **Percentiles** (`percentiles.png`) - P50/P95/P99 analysis
5. **Distribution** (`distribution.png`) - Violin plot
6. **Boxplot** (`boxplot.png`) - Statistical distribution
7. **Success Rate** (`success_rate.png`) - Success comparison

---

## Comparison Methodology

To compare SOLVENS with other frameworks:

1. **Same Tasks**: Use identical benchmark tasks
2. **Same Configuration**: Same model, parameters, iterations
3. **Same Environment**: Consistent system resources
4. **Same Measurement**: Identical metrics collection

### Frameworks for Comparison

| Framework | Status | Notes |
|-----------|--------|-------|
| SOLVENS | ✅ Implemented | Current focus |
| LangGraph | 🔜 Planned | Next comparison |
| CrewAI | 🔜 Planned | Future comparison |
| AutoGen | 🔜 Planned | Future comparison |
| OpenAI Swarm | 🔜 Planned | Future comparison |

---

## How to Run

### 1. Run Benchmarks

```bash
# Quick benchmark (3 iterations)
python benchmarks/scientific.py --iterations 3

# Standard benchmark (10 iterations)
python benchmarks/scientific.py --iterations 10

# Extended benchmark (30 iterations)
python benchmarks/scientific.py --iterations 30
```

### 2. Generate Plots

```bash
# Generate all plots
python benchmarks/plot_generator.py

# Custom output directory
python benchmarks/plot_generator.py --output my_results/plots
```

### 3. Export Data

```bash
# Results are automatically saved as:
benchmarks/scientific_output/
├── json/results.json    # Full data
├── csv/results.csv      # Spreadsheet format
└── plots/              # Visualizations
```

---

## Limitations

1. **Mock Mode**: Current benchmarks use simulation, not real API calls
2. **Single Framework**: Only SOLVENS benchmarked so far
3. **No Network Variance**: Local execution doesn't simulate API latency
4. **Short Duration**: Long-running benchmarks not yet conducted

---

## Environment Lock (Required for Reproducibility)

For reproducible benchmarks, the following must be fixed:

```yaml
environment:
  python_version: "3.12"          # Exact version
  packages:
    openai: "1.12.0"              # Pinned versions
    anthropic: "0.21.0"
    langgraph: "0.0.20"
  model: "gpt-4o-mini"             # Exact model
  temperature: 0                     # Fixed
  max_tokens: 2048                  # Fixed
  seed: null                        # Not used for LLM calls
  
system:
  timestamp_utc: "2025-01-17T00:00:00Z"
  hardware: "standard"               # Consistent hardware tier
  
network:
  region: "us-east-1"              # Same region for all
```

---

## Benchmark Phases

### Phase 2.0: Mock Validation ✅
- Framework structure validated
- Mock results generated
- **DO NOT use for scientific claims**

### Phase 2.1-A: Calibration (50 runs)
- [ ] Configure API keys
- [ ] Run 50 runs per framework
- [ ] Verify token counting
- [ ] Verify cost calculation
- [ ] Manual CSV review
- [ ] Compare with API bill

### Phase 2.1-B: Full Production (3000 runs)
- [ ] Run 1000 runs per framework
- [ ] Generate final reports
- [ ] Statistical analysis
- [ ] Publish results

### Phase 2.2: Framework Comparisons
- [ ] Benchmark LangGraph
- [ ] Benchmark CrewAI
- [ ] Benchmark AutoGen
- [ ] Generate comparative reports

### Phase 2.3: Stress Testing
- [ ] Long-duration benchmarks (hours)
- [ ] High-concurrency tests
- [ ] Memory leak detection
- [ ] CPU profiling

---

## GO/NO-GO Criteria

### GO Criteria (Flexible)
- [ ] Benchmark reproducible
- [ ] Cost competitive (not necessarily cheapest)
- [ ] No worse than baselines
- [ ] Advantages demonstrated where they exist

### NO-GO Criteria
- [ ] Metrics not reproducible
- [ ] Unexpected costs (token multiplier bug)
- [ ] Statistical errors
- [ ] API errors not handled

---

## Citation

If you use these benchmarks, please cite:

```
@misc{solvens2025,
  title={SOLVENS CORE Scientific Benchmarks},
  author={Luis Alberto Burciaga Miker},
  year={2025},
  howpublished={\url{https://github.com/SolvensAmoris/solvens-core}}
}
```

---

## Contact

For questions about methodology or results:
- **Author:** Luis Alberto Burciaga Miker
- **Repository:** https://github.com/SolvensAmoris/solvens-core
- **Issues:** https://github.com/SolvensAmoris/solvens-core/issues
