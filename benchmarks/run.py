"""
SOLVENS CORE - Benchmark Runner

Runs reproducible benchmarks with objective measurements.
"""

import time
import uuid
import argparse
from pathlib import Path
from typing import Optional
from cosmos.parser.parser import Parser
from cosmos.dag import DAG, build_dag_from_ast
from benchmarks.config import BenchmarkConfig, BENCHMARK_CONFIGS
from benchmarks.metrics import (
    MetricsCollector, 
    RunMetrics, 
    NodeExecution, 
    ExecutionStatus
)
from benchmarks.reporter import BenchmarkReporter


class MockProvider:
    """Mock provider for reproducible benchmarks."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.call_count = 0
        self.token_count = 0
    
    def chat(self, prompt: str, **kwargs) -> tuple[str, int, int]:
        """Simulate a chat completion."""
        self.call_count += 1
        
        # Simulate latency
        latency_s = self.config.mock_latency_ms / 1000
        time.sleep(latency_s)
        
        # Calculate mock tokens
        input_tokens = len(prompt.split()) * 1.3  # ~1.3 tokens per word
        output_tokens = self.config.max_tokens * 0.3  # ~30% of max
        total_tokens = int(input_tokens + output_tokens)
        
        self.token_count += total_tokens
        
        # Generate mock response
        response = f"[Mock response {self.call_count} - {total_tokens} tokens]"
        
        return response, int(input_tokens), int(output_tokens)


class SolvensBenchmark:
    """Benchmark harness for SOLVENS CORE."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.provider = MockProvider(config)
    
    def create_workflow(self, name: str = "test") -> str:
        """Create a test workflow in Cosmos DSL."""
        nodes = self.config.dag_nodes
        
        workflow = f'''# Benchmark workflow: {name}
provider openai {{
    type = "openai"
    model = "gpt-4o-mini"
}}

task init {{
    provider = "openai"
    depends_on = []
}}

'''
        
        for i in range(1, nodes):
            prev = f"process_{i-1}" if i > 1 else "init"
            workflow += f'''task process_{i} {{
    provider = "openai"
    depends_on = [{prev}]
}}

'''
        
        return workflow
    
    def run_single_benchmark(self, workflow_name: str) -> RunMetrics:
        """Run a single benchmark iteration."""
        run_id = str(uuid.uuid4())[:8]
        
        with MetricsCollector("solvens-core", workflow_name, run_id) as collector:
            # Create workflow
            workflow_code = self.create_workflow(workflow_name)
            
            # Parse
            parser = Parser(workflow_code)
            ast = parser.parse()
            
            # Build DAG
            dag = build_dag_from_ast(ast.statements)
            
            # Execute nodes
            for node_id in dag.nodes:
                node_start = time.perf_counter()
                response, input_tok, output_tok = self.provider.chat(
                    f"Execute {node_id}",
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                )
                node_end = time.perf_counter()
                
                node_exec = NodeExecution(
                    node_id=node_id,
                    node_type="task",
                    start_time=node_start,
                    end_time=node_end,
                    duration_ms=(node_end - node_start) * 1000,
                    input_tokens=input_tok,
                    output_tokens=output_tok,
                    cached=False,
                    provider=self.config.provider,
                    model=self.config.model,
                    cost_usd=0.0,  # Mock mode = no cost
                )
                collector.add_node(node_exec)
                collector.sample_cpu()
            
            if collector.metrics:
                collector.metrics.dag_nodes = len(dag.nodes)
                collector.metrics.dag_edges = len(dag.edges)
        
        return collector.metrics


def run_benchmarks(
    config_name: str = "standard",
    output_dir: Optional[Path] = None,
) -> dict:
    """
    Run benchmarks with specified configuration.
    
    Returns paths to generated reports.
    """
    # Get configuration
    if config_name in BENCHMARK_CONFIGS:
        config = BENCHMARK_CONFIGS[config_name]
    else:
        config = BenchmarkConfig(experiment_name=config_name)
    
    if output_dir is None:
        output_dir = Path(f"benchmarks/output/{config_name}")
    
    print(f"Running {config_name} benchmarks...")
    print(f"  Iterations: {config.iterations}")
    print(f"  Warmup: {config.warmup_iterations}")
    print(f"  DAG nodes: {config.dag_nodes}")
    print()
    
    benchmark = SolvensBenchmark(config)
    all_metrics: list[RunMetrics] = []
    
    # Warmup runs
    print(f"Warmup ({config.warmup_iterations} runs)...")
    for i in range(config.warmup_iterations):
        benchmark.run_single_benchmark(f"warmup_{i}")
    
    # Actual benchmark runs
    print(f"Benchmark ({config.iterations} runs)...")
    for i in range(config.iterations):
        print(f"  Run {i+1}/{config.iterations}...", end=" ", flush=True)
        metrics = benchmark.run_single_benchmark(f"run_{i}")
        all_metrics.append(metrics)
        print(f"{metrics.total_duration_ms:.2f}ms, {metrics.total_tokens} tokens")
    
    # Generate reports
    print("\nGenerating reports...")
    reporter = BenchmarkReporter(output_dir, config)
    report_paths = reporter.generate_reports(all_metrics)
    
    print("\nReports generated:")
    for name, path in report_paths.items():
        print(f"  {name}: {path}")
    
    return report_paths


def main():
    parser = argparse.ArgumentParser(description="SOLVENS CORE Benchmark Runner")
    parser.add_argument(
        "--config",
        choices=["quick", "standard", "extended"],
        default="standard",
        help="Benchmark configuration"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for reports"
    )
    
    args = parser.parse_args()
    run_benchmarks(args.config, args.output)


if __name__ == "__main__":
    main()
