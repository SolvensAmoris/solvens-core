# Smoke test runner

Run from the repository root after installing the project dependencies:

```bash
python tests/smoke/run_smoke.py
```

The runner is intentionally named `run_smoke.py` so pytest does not collect its helper `test_result` function as a test case.
