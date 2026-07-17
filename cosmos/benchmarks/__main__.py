#!/usr/bin/env python3
"""
COSMOS Benchmarks CLI

Run: python -m cosmos.benchmarks [command]

Commands:
    run         Run benchmarks
    compare     Compare frameworks
    table       Generate markdown table
    workflow    Run specific workflow
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cosmos.benchmarks.runner import BenchmarkRunner


def run_benchmarks(args):
    """Run all benchmarks."""
    runner = BenchmarkRunner()
    
    print("=" * 60)
    print("  COSMOS BENCHMARK SUITE")
    print("  Scientific Performance Metrics")
    print("=" * 60)
    print()
    
    # Run COSMOS workflows
    print("Running COSMOS workflows...")
    workflows = ["crm_generator", "doc_writer", "audit_flow"]
    
    for wf in workflows:
        print(f"\n  {wf}...")
        result = runner.run_cosmos(wf)
        print(f"    Time: {result.execution_time_ms:.0f}ms")
        print(f"    Cost: ${result.cost_usd:.4f}")
        print(f"    Nodes: {result.dag_nodes_count}")
    
    # Run comparison frameworks
    if args.compare:
        print("\nRunning comparison frameworks...")
        
        print("\n  baseline (direct API)...")
        baseline = runner.run_baseline("Generate a complete CRM system")
        print(f"    Time: {baseline.execution_time_ms:.0f}ms")
        print(f"    Cost: ${baseline.cost_usd:.4f}")
        
        print("\n  langchain...")
        lc = runner.run_langchain("Generate a complete CRM system")
        print(f"    Time: {lc.execution_time_ms:.0f}ms")
        print(f"    Cost: ${lc.cost_usd:.4f}")
        
        print("\n  autogen...")
        ag = runner.run_autogen("Generate a complete CRM system")
        print(f"    Time: {ag.execution_time_ms:.0f}ms")
        print(f"    Cost: ${ag.cost_usd:.4f}")
    
    print()
    print("=" * 60)
    print("  COMPARISON TABLE")
    print("=" * 60)
    print()
    print(runner.generate_markdown_table())
    
    return 0


def show_table(args):
    """Generate markdown comparison table."""
    runner = BenchmarkRunner()
    print(runner.generate_markdown_table())
    return 0


def run_workflow(args):
    """Run a specific workflow."""
    runner = BenchmarkRunner()
    
    print(f"Running workflow: {args.workflow}")
    result = runner.run_cosmos(args.workflow)
    
    print()
    print(result)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="COSMOS Benchmark Suite"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run all benchmarks")
    run_parser.add_argument(
        "--compare", 
        action="store_true",
        help="Include comparison frameworks"
    )
    run_parser.set_defaults(func=run_benchmarks)
    
    # table command
    table_parser = subparsers.add_parser("table", help="Generate markdown table")
    table_parser.set_defaults(func=show_table)
    
    # workflow command
    wf_parser = subparsers.add_parser("workflow", help="Run specific workflow")
    wf_parser.add_argument("workflow", help="Workflow name")
    wf_parser.set_defaults(func=run_workflow)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default: run benchmarks
        args.compare = True
        return run_benchmarks(args)
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
