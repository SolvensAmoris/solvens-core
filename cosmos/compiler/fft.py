"""
Cosmos FFT Implementation
=========================

Cooley-Tukey Fast Fourier Transform.
Time complexity: O(n log n) vs DFT O(n²)

Author: Luis Alberto Burciaga Miker
License: Apache 2.0
"""

import numpy as np
from typing import Tuple, Union

ComplexArray = Union[np.ndarray, np.complex128]


def fft(x: ComplexArray) -> ComplexArray:
    """
    Compute FFT using Cooley-Tukey iterative algorithm.
    
    Args:
        x: Input signal (must be power of 2 length)
        
    Returns:
        FFT of input signal
        
    Time Complexity:
        O(n log n)
        
    Reference:
        Cooley, J.W. & Tukey, J.W. (1965). An algorithm for the machine
        calculation of complex Fourier series. Math. Comput., 19, 297-301.
    """
    x = np.asarray(x, dtype=np.complex128).copy()
    n = len(x)
    
    # Base case
    if n <= 1:
        return x
    
    # Must be power of 2
    if n & (n - 1):
        raise ValueError(f"Input length must be power of 2, got {n}")
    
    # Bit-reversal permutation
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        
        if i < j:
            x[i], x[j] = x[j], x[i]
    
    # Cooley-Tukey iterative FFT
    length = 2
    while length <= n:
        half_length = length >> 1
        theta = -np.pi / half_length
        w_step = np.exp(1j * theta)
        
        for i in range(0, n, length):
            w = 1 + 0j
            for j in range(i, i + half_length):
                u = x[j]
                t = w * x[j + half_length]
                x[j] = u + t
                x[j + half_length] = u - t
                w *= w_step
        
        length <<= 1
    
    return x


def ifft(X: ComplexArray) -> ComplexArray:
    """
    Compute inverse FFT.
    
    Args:
        X: FFT of signal
        
    Returns:
        Inverse FFT (time domain signal)
    """
    X = np.asarray(X, dtype=np.complex128)
    n = len(X)
    
    # Inverse FFT = conj(FFT(conj(X))) / n
    return np.conj(fft(np.conj(X))) / n


def verify_fft(size: int = 1024, seed: int = 42) -> Tuple[bool, float]:
    """
    Verify FFT against NumPy implementation.
    
    Args:
        size: Signal length (power of 2)
        seed: Random seed
        
    Returns:
        (is_correct, max_error)
    """
    np.random.seed(seed)
    x = np.random.rand(size) + 1j * np.random.rand(size)
    
    X_np = np.fft.fft(x)
    X_cosmos = fft(x)
    
    max_error = np.max(np.abs(X_np - X_cosmos))
    is_correct = max_error < 1e-10
    
    return is_correct, max_error


if __name__ == "__main__":
    import time
    
    print("Cosmos FFT Implementation")
    print("=" * 40)
    
    for size in [256, 1024, 4096]:
        print(f"\nSignal length: {size}")
        
        # Verify
        correct, error = verify_fft(size)
        print(f"Correctness: {'✓ PASS' if correct else '✗ FAIL'} (max error: {error:.2e})")
        
        # Benchmark
        x = np.random.rand(size) + 1j * np.random.rand(size)
        
        # NumPy
        t0 = time.perf_counter()
        X_np = np.fft.fft(x)
        t_np = time.perf_counter() - t0
        
        # Cosmos FFT
        t0 = time.perf_counter()
        X_cosmos = fft(x)
        t_fft = time.perf_counter() - t0
        
        print(f"NumPy FFT:  {t_np*1000:.3f}ms")
        print(f"Cosmos FFT: {t_fft*1000:.3f}ms")
        
        if t_fft > 0:
            speedup = t_np / t_fft
            print(f"Speedup:    {speedup:.2f}x")
