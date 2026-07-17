# Cosmos Benchmarks

Verifiable performance benchmarks for Cosmos Compiler.

## Reproduce Results

Anyone can verify these benchmarks by running:

```bash
git clone https://github.com/SolvensAmoris/solvens-core
cd solvens-core
pip install numpy
python benchmarks/run_benchmark.py
```

## Strassen Matrix Multiplication

### What is it?

Strassen's algorithm reduces matrix multiplication complexity from O(n³) to O(n²·⁸⁰⁷).

### Implementation

The implementation is **real Strassen**, not disguised NumPy:

- Source: [`cosmos/compiler/strassen.py`](https://github.com/SolvensAmoris/solvens-core/blob/main/cosmos/compiler/strassen.py)
- Uses actual divide-and-conquer with 7 recursive multiplications
- Verified against NumPy's BLAS implementation

### Verification

Every benchmark run validates correctness:

```python
correct = np.allclose(C_np, C_strassen, rtol=1e-10, atol=1e-10)
```

### Expected Results

| Size | NumPy dot | Cosmos Strassen | Speedup | Correct? |
|------|-----------|-----------------|---------|----------|
| 64x64 | ~0.1ms | ~0.2ms | 0.5x | ✓ |
| 128x128 | ~0.8ms | ~1.5ms | 0.5x | ✓ |
| 256x256 | ~6ms | ~12ms | 0.5x | ✓ |

**Note:** Strassen is slower than NumPy for small/medium matrices because:
1. NumPy uses highly-optimized BLAS libraries (OpenBLAS, MKL)
2. Strassen has recursion overhead
3. Cache effects favor standard multiplication for n < 512

Strassen wins theoretically but NumPy wins practically. This is expected.

## FFT (Fast Fourier Transform)

### What is it?

Cooley-Tukey iterative FFT with O(n log n) complexity.

### Implementation

Source: [`cosmos/compiler/fft.py`](https://github.com/SolvensAmoris/solvens-core/blob/main/cosmos/compiler/fft.py)

### Verification

```python
correct = np.allclose(X_np, X_cosmos, rtol=1e-10, atol=1e-10)
```

## Running Individual Benchmarks

```bash
# Strassen only
python -c "from cosmos.compiler.strassen import verify_strassen; print(verify_strassen(128))"

# FFT only
python -c "from cosmos.compiler.fft import verify_fft; print(verify_fft(1024))"
```

## Why These Benchmarks?

1. **Transparency:** Full source code available
2. **Reproducibility:** Fixed random seeds
3. **Verification:** Every run validates correctness
4. **Fairness:** Compare against industry-standard NumPy

## GitHub Actions

Benchmarks run on every PR to ensure no regressions.

## Contact

Luis Alberto Burciaga Miker  
luis@solvens.amoris
