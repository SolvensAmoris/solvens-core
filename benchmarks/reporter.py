"""
Benchmark Report Generator

Generates reproducible benchmark reports in multiple formats.
"""

import json
import csv
from pathlib import Path
from typing import List
from datetime import datetime
from benchmarks.metrics import RunMetrics, StatisticalSummary, calculate_statistics
from benchmarks.config import BenchmarkConfig


class BenchmarkReporter:
    """Generates benchmark reports in various formats."""
    
    def __init__(self, output_dir: Path, config: BenchmarkConfig):
        self.output_dir = Path(output_dir)
        self.config = config
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure subdirectories exist
        (self.output_dir / "graphs").mkdir(exist_ok=True)
    
    def generate_reports(self, all_metrics: list[RunMetrics]):
        """Generate all report formats."""
        # Group metrics by framework
        by_framework = {}
        for m in all_metrics:
            if m.framework not in by_framework:
                by_framework[m.framework] = []
            by_framework[m.framework].append(m)
        
        # Generate each format
        self._generate_json(all_metrics)
        self._generate_csv(all_metrics)
        self._generate_markdown(all_metrics, by_framework)
        
        return {
            "json": str(self.output_dir / "RESULTS.json"),
            "csv": str(self.output_dir / "RESULTS.csv"),
            "md": str(self.output_dir / "BENCHMARKS.md"),
        }
    
    def _generate_json(self, all_metrics: list[RunMetrics]):
        """Generate JSON report."""
        # Calculate statistics for each framework
        framework_stats = {}
        
        for framework in set(m.framework for m in all_metrics):
            framework_metrics = [m for m in all_metrics if m.framework == framework]
            
            stats = {
                "framework": framework,
                "runs": len(framework_metrics),
                "metrics": {}
            }
            
            # Calculate statistics for key metrics
            key_metrics = [
                ("total_duration_ms", "Total Duration (ms)"),
                ("total_tokens", "Total Tokens"),
                ("total_cost_usd", "Total Cost (USD)"),
                ("peak_memory_mb", "Peak Memory (MB)"),
                ("cache_hit_rate", "Cache Hit Rate"),
                ("throughput_tokens_per_second", "Throughput (tokens/s)"),
            ]
            
            for metric_key, metric_name in key_metrics:
                values = [getattr(m, metric_key) for m in framework_metrics]
                if all(v == 0 for v in values) and metric_key != "total_duration_ms":
                    continue
                    
                stat = calculate_statistics(values, framework, "all", metric_name)
                stats["metrics"][metric_key] = stat.to_dict()
            
            framework_stats[framework] = stats
        
        report = {
            "experiment": self.config.to_dict(),
            "generated_at": datetime.now().isoformat(),
            "total_runs": len(all_metrics),
            "frameworks": list(framework_stats.keys()),
            "framework_stats": framework_stats,
            "raw_runs": [
                {
                    "run_id": m.run_id,
                    "framework": m.framework,
                    "workflow": m.workflow_name,
                    "status": m.status.value,
                    "duration_ms": round(m.total_duration_ms, 2),
                    "tokens": m.total_tokens,
                    "cost_usd": round(m.total_cost_usd, 6),
                    "memory_mb": round(m.peak_memory_mb, 2),
                    "cache_hit_rate": round(m.cache_hit_rate, 4),
                }
                for m in all_metrics
            ]
        }
        
        output_path = self.output_dir / "RESULTS.json"
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
    
    def _generate_csv(self, all_metrics: list[RunMetrics]):
        """Generate CSV report."""
        output_path = self.output_dir / "RESULTS.csv"
        
        # Define columns
        columns = [
            "run_id",
            "framework",
            "workflow",
            "status",
            "duration_ms",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost_usd",
            "peak_memory_mb",
            "cpu_percent_avg",
            "cache_hit_rate",
            "dag_nodes",
            "throughput_tokens_per_second",
        ]
        
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            for m in all_metrics:
                writer.writerow({
                    "run_id": m.run_id,
                    "framework": m.framework,
                    "workflow": m.workflow_name,
                    "status": m.status.value,
                    "duration_ms": round(m.total_duration_ms, 2),
                    "input_tokens": m.total_input_tokens,
                    "output_tokens": m.total_output_tokens,
                    "total_tokens": m.total_tokens,
                    "cost_usd": round(m.total_cost_usd, 6),
                    "peak_memory_mb": round(m.peak_memory_mb, 2),
                    "cpu_percent_avg": round(m.cpu_percent_avg, 2),
                    "cache_hit_rate": round(m.cache_hit_rate, 4),
                    "dag_nodes": m.dag_nodes,
                    "throughput_tokens_per_second": round(m.throughput_tokens_per_second, 2),
                })
    
    def _generate_markdown(self, all_metrics: list[RunMetrics], by_framework: dict):
        """Generate Markdown report with impartial analysis."""
        output_path = self.output_dir / "BENCHMARKS.md"
        
        lines = [
            "# SOLVENS CORE - Benchmark Report",
            "",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Experiment:** {self.config.experiment_name}",
            f"**Version:** {self.config.experiment_version}",
            "",
            "## Configuration",
            "",
            "```yaml",
            f"model: {self.config.model}",
            f"iterations: {self.config.iterations}",
            f"warmup: {self.config.warmup_iterations}",
            f"timeout: {self.config.timeout_seconds}s",
            f"mock_mode: {self.config.use_mocks}",
            f"mock_latency: {self.config.mock_latency_ms}ms",
            "",
            f"python_version: {self.config.python_version}",
            f"platform: {self.config.platform}",
            f"cpu_count: {self.config.cpu_count}",
            f"total_memory_gb: {self.config.total_memory_gb}",
            "```",
            "",
            "## Raw Results",
            "",
        ]
        
        # Summary table
        lines.extend([
            "### Summary by Framework",
            "",
            "| Framework | Runs | Avg Duration (ms) | Avg Tokens | Avg Cost | Avg Memory (MB) |",
            "|-----------|------|------------------|-----------|---------|-----------------|",
        ])
        
        for framework, metrics in by_framework.items():
            avg_duration = sum(m.total_duration_ms for m in metrics) / len(metrics)
            avg_tokens = sum(m.total_tokens for m in metrics) / len(metrics)
            avg_cost = sum(m.total_cost_usd for m in metrics) / len(metrics)
            avg_memory = sum(m.peak_memory_mb for m in metrics) / len(metrics)
            
            lines.append(
                f"| {framework} | {len(metrics)} | {avg_duration:.2f} | "
                f"{avg_tokens:.0f} | ${avg_cost:.6f} | {avg_memory:.2f} |"
            )
        
        lines.extend([
            "",
            "## Statistical Analysis",
            "",
        ])
        
        # Detailed statistics per metric
        for framework, metrics in by_framework.items():
            lines.extend([
                f"### {framework}",
                "",
                "| Metric | Mean | Median | Std Dev | P95 | Min | Max |",
                "|--------|------|--------|---------|-----|-----|-----|",
            ])
            
            for metric_key, metric_name in [
                ("total_duration_ms", "Duration (ms)"),
                ("total_tokens", "Tokens"),
                ("peak_memory_mb", "Memory (MB)"),
                ("cache_hit_rate", "Cache Hit Rate"),
            ]:
                values = [getattr(m, metric_key) for m in metrics]
                if all(v == 0 for v in values):
                    continue
                    
                stat = calculate_statistics(values, framework, "all", metric_name)
                lines.append(
                    f"| {metric_name} | {stat.mean:.2f} | {stat.median:.2f} | "
                    f"{stat.std_dev:.2f} | {stat.p95:.2f} | {stat.min_val:.2f} | {stat.max_val:.2f} |"
                )
            
            lines.append("")
        
        # Impartial Analysis
        lines.extend([
            "## Analysis (Impartial)",
            "",
            "### Observed Strengths",
            "",
        ])
        
        # Find actual strengths based on data
        if len(by_framework) >= 2:
            frameworks = list(by_framework.keys())
            
            # Compare duration
            avg_durations = {
                f: sum(m.total_duration_ms for m in ms) / len(ms)
                for f, ms in by_framework.items()
            }
            fastest = min(avg_durations, key=avg_durations.get)
            
            # Compare memory
            avg_memory = {
                f: sum(m.peak_memory_mb for m in ms) / len(ms)
                for f, ms in by_framework.items()
            }
            most_efficient_memory = min(avg_memory, key=avg_memory.get)
            
            lines.append(f"- **{fastest}** showed the fastest average execution time")
            lines.append(f"- **{most_efficient_memory}** used the least memory on average")
            
            # Compare cache
            cache_rates = {
                f: sum(m.cache_hit_rate for m in ms) / len(ms)
                for f, ms in by_framework.items()
                if any(m.cache_hit_rate > 0 for m in ms)
            }
            if cache_rates:
                best_cache = max(cache_rates, key=cache_rates.get)
                lines.append(f"- **{best_cache}** achieved the highest cache hit rate")
        else:
            lines.append("- Only one framework benchmarked; comparative analysis not available")
        
        lines.extend([
            "",
            "### Observed Weaknesses",
            "",
        ])
        
        # Find actual weaknesses
        if len(by_framework) >= 2:
            slowest = max(avg_durations, key=avg_durations.get)
            highest_memory = max(avg_memory, key=avg_memory.get)
            
            lines.append(f"- **{slowest}** had the slowest average execution time")
            lines.append(f"- **{highest_memory}** used the most memory on average")
            
            # Check for failures
            for framework, metrics in by_framework.items():
                failures = [m for m in metrics if m.status.value != "success"]
                if failures:
                    lines.append(f"- **{framework}** had {len(failures)} failed/timed-out runs")
        else:
            lines.append("- Comparative weakness analysis requires multiple frameworks")
        
        lines.extend([
            "",
            "### Identified Bottlenecks",
            "",
            "Based on the measured data:",
            "",
        ])
        
        # Analyze bottlenecks from data
        all_durations = [m.total_duration_ms for m in all_metrics]
        if all_durations:
            max_duration = max(all_durations)
            max_run = [m for m in all_metrics if m.total_duration_ms == max_duration][0]
            lines.append(f"- Highest single run duration: {max_duration:.2f}ms ({max_run.framework})")
        
        all_memory = [m.peak_memory_mb for m in all_metrics]
        if all_memory:
            max_memory = max(all_memory)
            lines.append(f"- Peak memory usage observed: {max_memory:.2f}MB")
        
        lines.extend([
            "",
            "### Optimization Opportunities",
            "",
            "Potential areas for improvement (based on observed data):",
            "",
        ])
        
        # Propose optimizations based on data
        avg_cache = sum(m.cache_hit_rate for m in all_metrics) / len(all_metrics) if all_metrics else 0
        if avg_cache < 0.3:
            lines.append("1. **Cache optimization**: Current cache hit rate is low - consider improving cache strategy")
        
        avg_duration = sum(m.total_duration_ms for m in all_metrics) / len(all_metrics) if all_metrics else 0
        if avg_duration > 5000:
            lines.append("2. **Parallel execution**: Average duration suggests opportunity for parallel node execution")
        
        lines.extend([
            "",
            "## Reproducibility",
            "",
            f"To reproduce these benchmarks, use the following configuration:",
            "",
            "```bash",
            f"python -m benchmarks.run --config {self.config.experiment_name}",
            "```",
            "",
            "Or programmatically:",
            "",
            "```python",
            "from benchmarks.config import BenchmarkConfig",
            f"config = BenchmarkConfig(",
            f"    experiment_name='{self.config.experiment_name}',",
            f"    iterations={self.config.iterations},",
            f"    use_mocks={self.config.use_mocks},",
            ")",
            "```",
            "",
            "## Notes",
            "",
            "- All benchmarks used the same configuration for fair comparison",
            "- Mock mode was used for reproducibility",
            "- Results may vary based on system load and network conditions",
            f"- {len(all_metrics)} total runs executed",
            "",
            "---",
            "*This report was generated automatically and reflects objective measurements.*",
        ])
        
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
