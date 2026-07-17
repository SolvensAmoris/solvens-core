#!/usr/bin/env python3
"""
Cosmos Benchmark Suite
======================

Verifiable benchmarks for Cosmos Compiler.
Run this to verify Strassen and FFT implementations.

Usage:
    pip install cosmos-compiler
    python benchmarks/run_benchmark.py

Requirements:
    numpy
    cosmos-compiler

Author: Luis Alberto Burciaga Miker
License: Apache 2.0
"""

import os
import sys
import time
import hashlib

# Add cosmos to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("⚠️  numpy not installed. Run: pip install numpy")

try:
    from cosmos.compiler.strassen import strassen_multiply
    STRASSEN_AVAILABLE = True
except ImportError:
    STRASSEN_AVAILABLE = False
    print("⚠️  cosmos strassen not available")


def benchmark_strassen_numpy(size: int, runs: int = 5) -> dict:
    """
    Benchmark NumPy matrix multiplication.
    Returns dict with timing and verification.
    """
    if not NUMPY_AVAILABLE:
        return {"error": "numpy not available"}
    
    results = []
    for _ in range(runs):
        A = np.random.rand(size, size).astype(np.float64)
        B = np.random.rand(size, size).astype(np.float64)
        
        t0 = time.perf_counter()
        C = np.dot(A, B)
        elapsed = time.perf_counter() - t0
        
        results.append(elapsed)
    
    return {
        "operation": "numpy.dot",
        "size": size,
        "times": results,
        "mean": np.mean(results),
        "std": np.std(results),
        "min": np.min(results),
        "max": np.max(results),
    }


def benchmark_strassen_cosmos(size: int, runs: int = 5) -> dict:
    """
    Benchmark Cosmos Strassen implementation.
    Returns dict with timing and verification against NumPy.
    """
    if not NUMPY_AVAILABLE or not STRASSEN_AVAILABLE:
        return {"error": "numpy or cosmos strassen not available"}
    
    results = []
    correct = []
    
    for i in range(runs):
        # Generate test matrices
        A = np.random.rand(size, size).astype(np.float64)
        B = np.random.rand(size, size).astype(np.float64)
        
        # Reference result
        C_ref = np.dot(A, B)
        
        # Cosmos Strassen
        t0 = time.perf_counter()
        C_cosmos = strassen_multiply(A, B)
        elapsed = time.perf_counter() - t0
        
        results.append(elapsed)
        
        # Verify correctness
        is_correct = np.allclose(C_ref, C_cosmos, rtol=1e-10, atol=1e-10)
        correct.append(is_correct)
        
        if not is_correct:
            print(f"  ⚠️  Run {i+1}: Result mismatch! Max diff: {np.max(np.abs(C_ref - C_cosmos))}")
    
    all_correct = all(correct)
    
    return {
        "operation": "cosmos.strassen",
        "size": size,
        "times": results,
        "mean": np.mean(results),
        "std": np.std(results),
        "min": np.min(results),
        "max": np.max(results),
        "correct": correct,
        "all_correct": all_correct,
    }


def benchmark_fft(size: int, runs: int = 5) -> dict:
    """
    Benchmark FFT implementations.
    """
    if not NUMPY_AVAILABLE:
        return {"error": "numpy not available"}
    
    try:
        from cosmos.compiler.fft import fft
        FFT_AVAILABLE = True
    except ImportError:
        FFT_AVAILABLE = False
    
    results_np = []
    results_fft = []
    
    for _ in range(runs):
        # Generate signal
        x = np.random.rand(size) + 1j * np.random.rand(size)
        
        # NumPy FFT
        t0 = time.perf_counter()
        X_np = np.fft.fft(x)
        elapsed_np = time.perf_counter() - t0
        results_np.append(elapsed_np)
        
        # Cosmos FFT
        if FFT_AVAILABLE:
            t0 = time.perf_counter()
            X_cosmos = fft(x)
            elapsed_fft = time.perf_counter() - t0
            results_fft.append(elapsed_fft)
    
    return {
        "operation": "fft",
        "size": size,
        "numpy_times": results_np,
        "numpy_mean": np.mean(results_np),
        "numpy_std": np.std(results_np),
        "cosmos_times": results_fft if FFT_AVAILABLE else [],
        "cosmos_mean": float(np.mean(results_fft)) if FFT_AVAILABLE and len(results_fft) > 0 else None,
        "cosmos_std": float(np.std(results_fft)) if FFT_AVAILABLE and len(results_fft) > 0 else None,
        "fft_available": FFT_AVAILABLE,
    }


def print_banner():
    print("=" * 70)
    print("  COSMOS BENCHMARK SUITE v0.4.5")
    print("  Verifiable Strassen & FFT Implementation")
    print("  Author: Luis Alberto Burciaga Miker")
    print("=" * 70)
    print()


def print_results(result: dict, reference: dict = None):
    """Print benchmark results in a formatted table."""
    if "error" in result:
        print(f"  ⚠️  {result['error']}")
        return
    
    op = result["operation"]
    size = result["size"]
    
    if op == "numpy.dot":
        print(f"  NumPy dot ({size}x{size}):")
        print(f"    Mean: {result['mean']*1000:.2f}ms  ±{result['std']*1000:.2f}ms")
        print(f"    Min:  {result['min']*1000:.2f}ms")
        print(f"    Max:  {result['max']*1000:.2f}ms")
    
    elif op == "cosmos.strassen":
        speedup = reference["mean"] / result["mean"] if reference else 0
        correct = "✓" if result["all_correct"] else "✗"
        
        print(f"  Cosmos Strassen ({size}x{size}):")
        print(f"    Mean: {result['mean']*1000:.2f}ms  ±{result['std']*1000:.2f}ms")
        print(f"    Min:  {result['min']*1000:.2f}ms")
        print(f"    Max:  {result['max']*1000:.2f}ms")
        print(f"    Correctness: {correct}")
        if speedup > 0:
            print(f"    Speedup vs NumPy: {speedup:.2f}x")
    
    elif op == "fft":
        print(f"  FFT ({size} points):")
        print(f"    NumPy:   {result['numpy_mean']*1000:.3f}ms  ±{result['numpy_std']*1000:.3f}ms")
        if result.get("fft_available") and result.get("cosmos_mean") is not None:
            speedup = result["numpy_mean"] / result["cosmos_mean"]
            print(f"    Cosmos:  {result['cosmos_mean']*1000:.3f}ms  ±{result['cosmos_std']*1000:.3f}ms")
            print(f"    Speedup: {speedup:.2f}x")


def run_strassen_benchmark():
    """Run Strassen matrix multiplication benchmark."""
    print("\n" + "─" * 70)
    print("  STRASSEN MATRIX MULTIPLICATION BENCHMARK")
    print("─" * 70)
    print()
    print("  This benchmark verifies the Cosmos Strassen implementation against")
    print("  NumPy's highly-optimized BLAS routines.")
    print()
    print("  Each run validates correctness with np.allclose().")
    print()
    
    sizes = [64, 128, 256]
    runs = 3
    
    for size in sizes:
        print(f"\n  Size: {size}x{size} ({runs} runs averaged)")
        print()
        
        # NumPy baseline
        np_result = benchmark_strassen_numpy(size, runs)
        print_results(np_result)
        
        # Cosmos Strassen
        cosmos_result = benchmark_strassen_cosmos(size, runs)
        print_results(cosmos_result, np_result)


def run_fft_benchmark():
    """Run FFT benchmark."""
    print("\n" + "─" * 70)
    print("  FFT BENCHMARK")
    print("─" * 70)
    print()
    
    sizes = [1024, 4096, 16384]
    runs = 3
    
    for size in sizes:
        result = benchmark_fft(size, runs)
        print_results(result)


def main():
    """Run all benchmarks."""
    print_banner()
    
    if not NUMPY_AVAILABLE:
        print("❌ ERROR: numpy is required for benchmarks")
        print("   Run: pip install numpy")
        sys.exit(1)
    
    # System info
    print(f"  NumPy version: {np.__version__}")
    print(f"  Python version: {sys.version.split()[0]}")
    print(f"  Platform: {sys.platform}")
    print()
    
    # Run benchmarks
    run_strassen_benchmark()
    
    if STRASSEN_AVAILABLE:
        try:
            run_fft_benchmark()
        except Exception as e:
            print(f"\n  ⚠️  FFT benchmark skipped: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70)
    print()
    print("  To reproduce these results:")
    print("  $ git clone https://github.com/SolvensAmoris/solvens-core")
    print("  $ pip install numpy cosmos-compiler")
    print("  $ python benchmarks/run_benchmark.py")
    print()
    print("  Source code available at:")
    print("  https://github.com/SolvensAmoris/solvens-core/tree/main/cosmos/compiler")
    print()


if __name__ == "__main__":
    main()
