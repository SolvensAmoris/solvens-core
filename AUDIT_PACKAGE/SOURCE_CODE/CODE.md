# Source Code

This directory contains the complete source code of SOLVENS CORE.

## Structure

```
SOURCE_CODE/
├── solvens/          # Core package
├── cosmos/           # Cosmos language package
├── tests/            # Test suite
├── docs/             # Documentation
└── docker/           # Docker configuration
```

## Contents

- All Python source files
- Cosmos compiler implementation
- LLaMA audit suite (30 tests)
- API, CLI, Dashboard implementations
- Docker and systemd configurations

## Tests

Run all tests:
```bash
pytest
```

Run Cosmos tests:
```bash
python -m pytest cosmos/tests/ -v
```

## Compiler

Compile Cosmos files:
```bash
python -m cosmos.compiler <file.cosmos> --strict
```
