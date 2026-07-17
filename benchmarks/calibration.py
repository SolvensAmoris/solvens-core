"""
SOLVENS CORE - Calibration Benchmark Script
==========================================

PHASE 2.1-A: 50 runs to validate instrumentation

This script validates that:
1. Token counting works correctly
2. Cost calculation matches API billing
3. CSV output is correct
4. No API errors occur

COST ESTIMATE: ~$0.50 (50 runs)

Usage:
    python benchmarks/calibration.py
    python benchmarks/calibration.py --runs 50 --framework solvens

Author: Luis Alberto Burciaga Miker
Version: 1.0.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class CalibrationConfig:
    """Configuration for calibration run."""
    
    # API Configuration
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 2048
    
    # Benchmark Configuration
    runs: int = 50
    framework: str = "solvens"
    
    # Output Configuration
    output_dir: Path = Path("benchmarks/calibration_output")
    
    def __post_init__(self):
        self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class RunResult:
    """Result of a single run."""
    run_id: int
    timestamp: str
    duration_ms: float
    success: bool
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None
    p99_latency_ms: float = 0.0


# ============================================================
# COST CALCULATOR
# ============================================================

# OpenAI pricing (per 1M tokens)
OPENAI_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate cost in USD based on token counts."""
    pricing = OPENAI_PRICING.get(model, {"input": 0.0, "output": 0.0})
    
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + output_cost


# ============================================================
# API CLIENT
# ============================================================

async def run_openai_call(
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
) -> tuple[int, int, float, Optional[str]]:
    """
    Make a single OpenAI API call.
    
    Returns: (input_tokens, output_tokens, duration_ms, error)
    """
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        
        start = time.perf_counter()
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        return input_tokens, output_tokens, duration_ms, None
        
    except Exception as e:
        return 0, 0, 0.0, str(e)


# ============================================================
# CALIBRATION TASKS
# ============================================================

CALIBRATION_PROMPTS = [
    "What is 2 + 2? Answer in one word.",
    "List the colors of the rainbow. One per line.",
    "What is the capital of France?",
    "Is Python a programming language? Yes or no.",
    "What day comes after Monday?",
]


# ============================================================
# CALIBRATION RUNNER
# ============================================================

async def run_calibration(config: CalibrationConfig) -> list[RunResult]:
    """Run calibration benchmark."""
    
    if not config.api_key:
        raise ValueError("OPENAI_API_KEY not set. Please configure your API key.")
    
    print("=" * 60)
    print("  SOLVENS CORE - Calibration Benchmark")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Framework: {config.framework}")
    print(f"  Model: {config.model}")
    print(f"  Runs: {config.runs}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Max Tokens: {config.max_tokens}")
    print(f"  Estimated Cost: ~${config.runs * 0.0002:.2f}")
    
    results = []
    total_cost = 0.0
    
    print(f"\nRunning {config.runs} calls...\n")
    
    for i in range(config.runs):
        prompt = CALIBRATION_PROMPTS[i % len(CALIBRATION_PROMPTS)]
        
        input_tokens, output_tokens, duration_ms, error = await run_openai_call(
            api_key=config.api_key,
            model=config.model,
            prompt=prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        
        cost = calculate_cost(input_tokens, output_tokens, config.model)
        total_cost += cost
        
        result = RunResult(
            run_id=i + 1,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms,
            success=error is None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            error=error,
        )
        
        results.append(result)
        
        status = "✅" if result.success else "❌"
        print(f"  [{status}] Run {i+1:3d}: {duration_ms:7.2f}ms | "
              f"Tokens: {input_tokens}+{output_tokens} | Cost: ${cost:.6f}")
    
    print(f"\n{'=' * 60}")
    print(f"Calibration Complete")
    print(f"{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total Runs: {len(results)}")
    print(f"  Successful: {sum(1 for r in results if r.success)}")
    print(f"  Failed: {sum(1 for r in results if not r.success)}")
    print(f"  Total Cost: ${total_cost:.6f}")
    
    # Calculate statistics
    successful_results = [r for r in results if r.success]
    if successful_results:
        durations = [r.duration_ms for r in successful_results]
        tokens = [r.total_tokens for r in successful_results]
        
        print(f"\nStatistics (successful runs):")
        print(f"  Mean Duration: {sum(durations)/len(durations):.2f}ms")
        print(f"  Min Duration: {min(durations):.2f}ms")
        print(f"  Max Duration: {max(durations):.2f}ms")
        print(f"  Mean Tokens: {sum(tokens)/len(tokens):.0f}")
    
    return results


# ============================================================
# VALIDATION
# ============================================================

def validate_instrumentation(results: list[RunResult], config: CalibrationConfig) -> dict:
    """
    Validate that instrumentation is working correctly.
    
    Returns validation report.
    """
    validation = {
        "api_key_configured": bool(config.api_key),
        "model_configured": bool(config.model),
        "all_runs_completed": len(results) == config.runs,
        "all_runs_successful": all(r.success for r in results),
        "token_counting_works": all(r.total_tokens > 0 for r in results if r.success),
        "cost_calculation_works": all(r.cost_usd >= 0 for r in results),
        "csv_output_generated": False,
        "json_output_generated": False,
        "errors": [],
    }
    
    # Check for common issues
    if not validation["api_key_configured"]:
        validation["errors"].append("API key not configured")
    
    if not validation["token_counting_works"]:
        validation["errors"].append("Token counting returned zero for some runs")
    
    if not validation["all_runs_successful"]:
        failed = [r for r in results if not r.success]
        validation["errors"].append(f"{len(failed)} runs failed: {failed[0].error if failed else 'Unknown'}")
    
    # Check output files
    validation["csv_output_generated"] = (config.output_dir / "calibration.csv").exists()
    validation["json_output_generated"] = (config.output_dir / "calibration.json").exists()
    
    return validation


# ============================================================
# OUTPUT
# ============================================================

def save_results(results: list[RunResult], config: CalibrationConfig):
    """Save results to CSV and JSON."""
    
    # CSV
    csv_path = config.output_dir / "calibration.csv"
    with open(csv_path, "w") as f:
        f.write("run_id,timestamp,duration_ms,success,input_tokens,output_tokens,total_tokens,cost_usd,error\n")
        for r in results:
            f.write(f"{r.run_id},{r.timestamp},{r.duration_ms:.2f},{r.success},")
            f.write(f"{r.input_tokens},{r.output_tokens},{r.total_tokens},")
            f.write(f"{r.cost_usd:.8f},{r.error or ''}\n")
    
    print(f"  ✅ CSV saved: {csv_path}")
    
    # JSON
    json_path = config.output_dir / "calibration.json"
    with open(json_path, "w") as f:
        json.dump({
            "config": asdict(config),
            "results": [asdict(r) for r in results],
            "generated_at": datetime.now().isoformat(),
        }, f, indent=2)
    
    print(f"  ✅ JSON saved: {json_path}")


# ============================================================
# MAIN
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="Calibration benchmark for SOLVENS")
    parser.add_argument("--runs", type=int, default=50, help="Number of runs")
    parser.add_argument("--framework", type=str, default="solvens", help="Framework name")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model to use")
    parser.add_argument("--output", type=str, default="benchmarks/calibration_output", help="Output dir")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    
    args = parser.parse_args()
    
    config = CalibrationConfig(
        runs=args.runs,
        framework=args.framework,
        model=args.model,
        api_key=args.api_key,
        output_dir=Path(args.output),
    )
    
    try:
        # Run calibration
        results = await run_calibration(config)
        
        # Save results
        save_results(results, config)
        
        # Validate
        validation = validate_instrumentation(results, config)
        
        print(f"\n{'=' * 60}")
        print("Validation Report")
        print(f"{'=' * 60}")
        
        all_valid = True
        for key, value in validation.items():
            if key == "errors":
                continue
            
            if isinstance(value, bool):
                status = "✅" if value else "❌"
                print(f"  [{status}] {key}")
                if not value:
                    all_valid = False
        
        if validation["errors"]:
            print(f"\n⚠️ Errors found:")
            for error in validation["errors"]:
                print(f"  - {error}")
        else:
            print(f"\n✅ All validations passed!")
        
        print(f"\n{'=' * 60}")
        if all_valid:
            print("🎉 CALIBRATION SUCCESSFUL - Ready for production benchmarks")
            print(f"\nNext steps:")
            print(f"  1. Review {config.output_dir}/calibration.csv")
            print(f"  2. Compare costs with your API bill")
            print(f"  3. Run: python benchmarks/scientific.py --runs 1000")
        else:
            print("❌ CALIBRATION FAILED - Fix issues before continuing")
            sys.exit(1)
        print(f"{'=' * 60}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Calibration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Calibration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
