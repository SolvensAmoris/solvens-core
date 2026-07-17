#!/usr/bin/env python3
"""
CLI for COSMOS Benchmarks

Usage:
    python benchmarks/cli.py run --compare-all
    python benchmarks/cli.py table
"""

import sys
import argparse
from pathlib import Path

# Add cosmos to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos.benchmarks.runner import BenchmarkRunner


def main():
    parser = argparse.ArgumentParser(
        description="COSMOS Benchmark Suite - Scientific Performance Metrics"
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "table"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="Include comparison frameworks (LangChain, AutoGen)"
    )
    
    parser.add_argument(
        "--workflow",
        help="Run specific workflow"
    )
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner()
    
    if args.command == "table":
        runner.compare_all()
        print(runner.generate_markdown_table())
        return 0
    
    # Run command
    print("=" * 70)
    print("  COSMOS BENCHMARK SUITE")
    print("  Scientific Performance Metrics")
    print("  Author: Luis Alberto Burciaga Miker")
    print("=" * 70)
    print()
    
    if args.workflow:
        # Single workflow
        result = runner.run_cosmos(args.workflow)
        print(result)
    else:
        # All workflows
        workflows = ["crm_generator", "doc_writer", "audit_flow"]
        
        print("Running COSMOS workflows...")
        for wf in workflows:
            print(f"\n  {wf}:")
            result = runner.run_cosmos(wf)
            print(f"    Time: {result.execution_time_ms:.1f}ms")
            print(f"    Cost: ${result.cost_usd:.4f}")
            print(f"    Nodes: {result.dag_nodes_count}")
            print(f"    Tokens: {result.tokens_consumed:,}")
        
        if args.compare_all:
            print("\n" + "=" * 70)
            print("  COMPARISON FRAMEWORKS")
            print("=" * 70)
            
            # Baseline
            baseline = runner.run_baseline("Generate a complete CRM system")
            print(f"\n  Baseline (direct API):")
            print(f"    Time: {baseline.execution_time_ms:.1f}ms")
            print(f"    Cost: ${baseline.cost_usd:.4f}")
            
            # LangChain
            lc = runner.run_langchain("Generate a complete CRM system")
            print(f"\n  LangChain:")
            print(f"    Time: {lc.execution_time_ms:.1f}ms")
            print(f"    Cost: ${lc.cost_usd:.4f}")
            print(f"    Memory: {lc.peak_memory_mb:.0f}MB (overhead)")
            
            # AutoGen
            ag = runner.run_autogen("Generate a complete CRM system")
            print(f"\n  AutoGen:")
            print(f"    Time: {ag.execution_time_ms:.1f}ms")
            print(f"    Cost: ${ag.cost_usd:.4f}")
            print(f"    Memory: {ag.peak_memory_mb:.0f}MB (overhead)")
        
        print("\n" + "=" * 70)
        print("  COMPARISON TABLE")
        print("=" * 70)
        print()
        print(runner.generate_markdown_table())
        
        print("\n  For detailed results, run: python benchmarks/run_benchmark.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
