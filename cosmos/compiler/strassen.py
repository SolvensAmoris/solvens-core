"""
Cosmos Strassen Implementation
==============================

Strassen's algorithm for matrix multiplication.
Time complexity: O(n^2.807) vs standard O(n^3)

This is the REAL Strassen implementation used in benchmarks.
Not numpy.dot disguised - actual divide-and-conquer.

Author: Luis Alberto Burciaga Miker
License: Apache 2.0

Reference:
    Strassen, V. (1969). Gaussian Elimination is Not Optimal.
    Numerische Mathematik, 13(4), 354-356.
"""

import numpy as np
from typing import Tuple


def pad_matrix(A: np.ndarray) -> np.ndarray:
    """Pad matrix to nearest power of 2."""
    n, m = A.shape
    if n == m and (n & (n - 1)) == 0:
        return A
    
    size = max(n, m)
    size = 2 ** int(np.ceil(np.log2(size)))
    
    result = np.zeros((size, size), dtype=A.dtype)
    result[:n, :m] = A
    return result


def strassen_multiply(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Multiply two matrices using Strassen's algorithm.
    
    Args:
        A: First matrix (n x n)
        B: Second matrix (n x n)
        
    Returns:
        Matrix product A @ B
        
    Time Complexity:
        T(n) = 7T(n/2) + O(n^2)
        Solves to: O(n^2.807)
        
    Space Complexity:
        O(n^2) for temporary matrices
    """
    A = np.asarray(A)
    B = np.asarray(B)
    
    # Handle non-square matrices
    if A.shape != B.shape:
        raise ValueError("Matrices must be square and same size")
    
    n = A.shape[0]
    
    # Base case: use standard multiplication for small matrices
    if n <= 64:
        return np.dot(A, B)
    
    # Pad to power of 2
    if (n & (n - 1)) != 0:
        A = pad_matrix(A)
        B = pad_matrix(B)
        padded = True
    else:
        padded = False
    
    size = A.shape[0]
    half = size // 2
    
    # Split matrices into quadrants
    A11, A12 = A[:half, :half], A[:half, half:]
    A21, A22 = A[half:, :half], A[half:, half:]
    
    B11, B12 = B[:half, :half], B[:half, half:]
    B21, B22 = B[half:, :half], B[half:, half:]
    
    # Strassen's 7 multiplications (vs 8 for standard)
    # M1 = (A11 + A22)(B11 + B22)
    M1 = strassen_multiply(A11 + A22, B11 + B22)
    
    # M2 = (A21 + A22)B11
    M2 = strassen_multiply(A21 + A22, B11)
    
    # M3 = A11(B12 - B22)
    M3 = strassen_multiply(A11, B12 - B22)
    
    # M4 = A22(B21 - B11)
    M4 = strassen_multiply(A22, B21 - B11)
    
    # M5 = (A11 + A12)B22
    M5 = strassen_multiply(A11 + A12, B22)
    
    # M6 = (A21 - A11)(B11 + B12)
    M6 = strassen_multiply(A21 - A11, B11 + B12)
    
    # M7 = (A12 - A22)(B21 + B22)
    M7 = strassen_multiply(A12 - A22, B21 + B22)
    
    # Combine results
    C11 = M1 + M4 - M5 + M7
    C12 = M3 + M5
    C21 = M2 + M4
    C22 = M1 - M2 + M3 + M6
    
    # Combine quadrants
    C = np.vstack([np.hstack([C11, C12]), np.hstack([C21, C22])])
    
    # Return original size if padded
    if padded:
        return C[:n, :n]
    
    return C


def verify_strassen(n: int = 128, seed: int = 42) -> bool:
    """
    Verify Strassen implementation against NumPy.
    
    Args:
        n: Matrix size
        seed: Random seed for reproducibility
        
    Returns:
        True if implementations match
    """
    np.random.seed(seed)
    A = np.random.rand(n, n)
    B = np.random.rand(n, n)
    
    C_np = np.dot(A, B)
    C_strassen = strassen_multiply(A, B)
    
    return np.allclose(C_np, C_strassen, rtol=1e-10, atol=1e-10)


if __name__ == "__main__":
    import time
    
    print("Cosmos Strassen Implementation")
    print("=" * 40)
    
    for size in [64, 128, 256]:
        print(f"\nMatrix size: {size}x{size}")
        
        # Verify correctness
        correct = verify_strassen(size)
        print(f"Correctness: {'✓ PASS' if correct else '✗ FAIL'}")
        
        # Benchmark
        A = np.random.rand(size, size)
        B = np.random.rand(size, size)
        
        # NumPy
        t0 = time.perf_counter()
        C_np = np.dot(A, B)
        t_np = time.perf_counter() - t0
        
        # Strassen
        t0 = time.perf_counter()
        C_strassen = strassen_multiply(A, B)
        t_strassen = time.perf_counter() - t0
        
        print(f"NumPy dot:   {t_np*1000:.2f}ms")
        print(f"Strassen:    {t_strassen*1000:.2f}ms")
        
        if t_strassen > 0:
            speedup = t_np / t_strassen
            print(f"Speedup:     {speedup:.2f}x")
