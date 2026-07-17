#!/usr/bin/env python3
"""
scripts/benchmark.py
===================

Benchmark Cosmos vs Terraform
============================

Compares Cosmos DSL compilation speed against Terraform validate.

Usage:
    python scripts/benchmark.py --files 1000
    python scripts/benchmark.py --compare-terraform

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import asyncio
import hashlib
import json
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.solvens_agent import CosmosCompilerAgent, Status


# ============================================================
# BENCHMARK CONFIG
# ============================================================

@dataclass
class BenchmarkConfig:
    """Configuration for benchmark."""
    num_files: int = 100
    num_e401: int = 1
    num_iterations: int = 3
    output_dir: str = "benchmark_results"
    compare_terraform: bool = False


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    total_files: int
    valid_files: int
    error_files: int
    e401_files: int
    total_time_ms: float
    avg_time_ms: float
    cache_hits: int = 0
    fail_fast_ms: float = 0
    throughput: float = 0


@dataclass
class BenchmarkReport:
    """Full benchmark report."""
    config: BenchmarkConfig
    results: List[BenchmarkResult]
    summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================
# COSMOS FILE GENERATORS
# ============================================================

class CosmosGenerator:
    """Generate Cosmos test files."""
    
    MODELS = ["claude-3-sonnet", "gpt-4", "gemini", "llama3", "mistral"]
    
    @staticmethod
    def generate_valid(num_nodes: int = 5) -> str:
        """Generate a valid Cosmos file."""
        code = "cosmos Benchmark {\n"
        code += "    sun CentralOrchestrator\n\n"
        
        for i in range(num_nodes):
            model = random.choice(CosmosGenerator.MODELS)
            code += f'    planet Task{i} {{\n'
            code += f'        model: {model}\n'
            
            if random.random() > 0.5:
                duration = random.randint(10, 120)
                code += f'        duration: {duration}\n'
            
            if random.random() > 0.7 and i > 0:
                connects_to = random.randint(0, i - 1)
                code += f'        connects_to: Task{connects_to}\n'
            
            code += "    }\n\n"
        
        code += "}\nend\n"
        return code
    
    @staticmethod
    def generate_e401() -> str:
        """Generate a file with E401 temporal violation."""
        start = random.randint(50, 150)
        end = random.randint(10, start - 1)
        
        code = "cosmos E401Test {\n"
        code += "    planet BadTask {\n"
        code += f"        start_after: {start}\n"
        code += f"        end_before: {end}\n"
        code += "        model: claude-3-sonnet\n"
        code += "    }\n"
        code += "}\nend\n"
        return code


class TerraformComparator:
    """Mock Terraform comparator for benchmark."""
    
    @staticmethod
    async def validate(file_content: str, filepath: str) -> Dict[str, Any]:
        """Simulate terraform validate."""
        start = time.time()
        await asyncio.sleep(0.005)
        elapsed_ms = (time.time() - start) * 1000
        
        return {
            "valid": True,
            "elapsed_ms": elapsed_ms,
            "error": None
        }


# ============================================================
# BENCHMARK RUNNER
# ============================================================

class BenchmarkRunner:
    """Runs benchmarks."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.agent = CosmosCompilerAgent(fail_fast=True)
        self.cosmos_gen = CosmosGenerator()
        self.results: List[BenchmarkResult] = []
    
    def generate_test_files(self) -> List[Dict[str, Any]]:
        """Generate test files for benchmark."""
        files = []
        
        for i in range(self.config.num_files - self.config.num_e401):
            files.append({
                "id": f"valid_{i}",
                "content": self.cosmos_gen.generate_valid(),
                "type": "valid"
            })
        
        for i in range(self.config.num_e401):
            files.append({
                "id": f"e401_{i}",
                "content": self.cosmos_gen.generate_e401(),
                "type": "e401"
            })
        
        random.shuffle(files)
        return files
    
    async def run_cosmos_benchmark(self, files: List[Dict]) -> BenchmarkResult:
        """Run Cosmos benchmark."""
        total_start = time.time()
        
        valid_count = 0
        error_count = 0
        e401_count = 0
        fail_fast_time = 0
        
        for f in files:
            start = time.time()
            result = await self.agent.run(f["content"])
            elapsed = (time.time() - start) * 1000
            
            if result.status == Status.APPROVED:
                valid_count += 1
            else:
                error_count += 1
                if result.metadata.get("error_code") == "TemporalConstraintViolation":
                    e401_count += 1
                    fail_fast_time = max(fail_fast_time, elapsed)
        
        total_time = (time.time() - total_start) * 1000
        
        return BenchmarkResult(
            total_files=len(files),
            valid_files=valid_count,
            error_files=error_count,
            e401_files=e401_count,
            total_time_ms=total_time,
            avg_time_ms=total_time / len(files),
            throughput=len(files) / (total_time / 1000)
        )
    
    async def run(self) -> BenchmarkReport:
        """Run full benchmark."""
        print("=" * 60)
        print("COSMOS BENCHMARK v0.4.5-rc1")
        print("=" * 60)
        print(f"Files: {self.config.num_files}")
        print(f"E401 files: {self.config.num_e401}")
        print(f"Iterations: {self.config.num_iterations}")
        print()
        
        files = self.generate_test_files()
        
        for i in range(self.config.num_iterations):
            print(f"Iteration {i + 1}/{self.config.num_iterations}...")
            result = await self.run_cosmos_benchmark(files)
            self.results.append(result)
            print(f"  Total: {result.total_time_ms:.2f}ms")
            print(f"  Avg: {result.avg_time_ms:.2f}ms/file")
            print()
        
        summary = self._calculate_summary()
        
        return BenchmarkReport(
            config=self.config,
            results=self.results,
            summary=summary
        )
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate benchmark summary."""
        total_times = [r.total_time_ms for r in self.results]
        avg_times = [r.avg_time_ms for r in self.results]
        
        return {
            "total_files_processed": sum(r.total_files for r in self.results),
            "avg_time_per_file_ms": statistics.mean(avg_times),
            "avg_time_std_ms": statistics.stdev(avg_times) if len(avg_times) > 1 else 0,
            "throughput_avg": statistics.mean(r.throughput for r in self.results),
            "valid_files_total": sum(r.valid_files for r in self.results),
            "error_files_total": sum(r.error_files for r in self.results),
            "e401_files_total": sum(r.e401_files for r in self.results),
        }


class BenchmarkReporter:
    """Generate benchmark reports."""
    
    @staticmethod
    def to_markdown(report: BenchmarkReport) -> str:
        """Generate Markdown report."""
        s = report.summary
        
        md = f"""# Cosmos Benchmark Report
=====================

**Date:** {report.timestamp}  
**Version:** 0.4.5-rc1  
**Files Tested:** {report.config.num_files}  
**Iterations:** {report.config.num_iterations}

## Summary

| Metric | Value |
|--------|-------|
| Total Files | {s.get('total_files_processed', 0)} |
| Valid Files | {s.get('valid_files_total', 0)} |
| Error Files | {s.get('error_files_total', 0)} |
| E401 Files | {s.get('e401_files_total', 0)} |
| **Avg Time/File** | **{s.get('avg_time_per_file_ms', 0):.2f}ms** |
| Throughput | {s.get('throughput_avg', 0):.1f} files/sec |

## Iteration Details

| Iteration | Total Time | Avg/File | Throughput |
|-----------|------------|----------|------------|
"""
        
        for i, r in enumerate(report.results, 1):
            md += f"| {i} | {r.total_time_ms:.2f}ms | {r.avg_time_ms:.2f}ms | {r.throughput:.1f} files/s |\n"
        
        md += f"""

## Key Findings

"""
        
        if s.get('avg_time_per_file_ms', 100) < 10:
            md += "- ✅ **Excellent Performance**: Sub-10ms average compilation time\n"
        elif s.get('avg_time_per_file_ms', 100) < 50:
            md += "- ✅ **Good Performance**: Under 50ms average compilation time\n"
        
        md += f"""
- 📊 **Consistency**: {'±' + f"{s.get('avg_time_std_ms', 0):.2f}ms" if s.get('avg_time_std_ms', 0) > 0 else 'Stable'} variance

---

*Generated by Cosmos Benchmark v0.4.5-rc1*
"""
        
        return md


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cosmos Benchmark")
    parser.add_argument("--files", type=int, default=100)
    parser.add_argument("--e401", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--output", default="benchmark_results")
    
    args = parser.parse_args()
    
    config = BenchmarkConfig(
        num_files=args.files,
        num_e401=args.e401,
        num_iterations=args.iterations,
        output_dir=args.output
    )
    
    os.makedirs(config.output_dir, exist_ok=True)
    
    runner = BenchmarkRunner(config)
    report = asyncio.run(runner.run())
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    md_report = BenchmarkReporter.to_markdown(report)
    md_path = os.path.join(config.output_dir, f"benchmark_{timestamp}.md")
    with open(md_path, "w") as f:
        f.write(md_report)
    print(f"\n📄 Report: {md_path}")
    print(md_report)


if __name__ == "__main__":
    main()
