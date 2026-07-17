# Changelog

All notable changes to SOLVENS CORE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.5.1-rc1] - 2025-01-17 - "SmartRouter Migration"

### Changed

- **SmartRouter Migration**
  - Copied `solvens/router/smart_router.py` → `cosmos/router/smart_router.py`
  - Updated `cosmos/moat/moat_executor.py` to use new import
  - Added deprecation warning to `solvens/router/smart_router.py`
  - SmartRouter now resides in cosmos/ as architecture intended

### Fixed

- SmartRouter dependency resolved

---

## [0.5.0-rc1] - 2025-01-17 - "Architectural Consolidation"

### Added

- **New Benchmark System** (`benchmarks/`)
  - Reproducible benchmark configuration
  - Statistical analysis (mean, median, std, percentiles)
  - Multiple output formats (JSON, CSV, Markdown)
  - Impartial analysis reports

- **Architecture Documentation** (`docs/ARCHITECTURE.md`)
  - Complete system overview
  - Package structure
  - Data flow diagrams
  - Interface definitions

### Changed

- **Phase 1.5: Architectural Consolidation**
  - Migrated `visualizer/` from `solvens/cosmos/` to `cosmos/`
  - Migrated `canonicalizer.py` to `cosmos/`
  - Migrated `moat/` to `cosmos/`
  - `cosmos/` is now the sole source of truth

### Fixed

- Fixed Cosmos Parser syntax issues (block syntax `{...}`)
- Fixed `datetime.utcnow()` deprecation (Python 3.12+)
- Fixed RBAC security: generates random secret if `SOLVENS_SECRET_KEY` not set
- Fixed import errors in `web_preview.py`
- Fixed `moat/__init__.py` exports

### Removed

- Deleted `solvens/cosmos/canonicalizer.py.backup` (unused backup)
- Deleted `solvens/cosmos/canonicalizer_production.py` (unused code)

### Documentation

- Updated `ARCHITECTURE.md` with new diagrams
- Added `benchmarks/EXPERIMENTAL_BENCHMARKS.md`
- Added `benchmarks/README.md`

### Security

- RBAC secret key validation
- No default secrets in production

---

## [1.0.0] - 2025-01-17

### Added

#### Core Components
- **Parser**: Cosmos DSL parser with support for providers, agents, tasks, and DAGs
- **AST**: Abstract Syntax Tree with visitor pattern
- **Runtime**: Cost safety, budget management, and rate limiting

#### Security
- **RBAC**: Full role-based access control with 6 roles (OWNER, ADMIN, EDITOR, DEVELOPER, VIEWER, AUDITOR)
- **API Keys**: Scoped API keys with expiration
- **Audit Logging**: Immutable audit trail for all operations

#### Providers
- **BaseProvider Interface**: Unified interface for all LLM providers
- **LLMInterface**: Centralized LLM access with automatic failover
- **Cost Estimator**: Pre-execution cost prediction

#### CLI
- `solvens version`: Show version
- `solvens init`: Initialize new project
- `solvens compile`: Compile workflow
- `solvens validate`: Validate workflow
- `solvens simulate`: Simulate without execution
- `solvens run`: Execute workflow
- `solvens explain`: Show DAG structure
- `solvens doctor`: Check configuration
- `solvens benchmark`: Run performance tests

#### Docker
- `Dockerfile`: Multi-stage production build
- `docker-compose.yml`: Full stack with Redis, Ollama, PostgreSQL
- `docker/Dockerfile.cli`: Standalone CLI container

#### Testing
- Integration tests for parser, CLI, RBAC, cost safety
- 10/10 tests passing

### Changed

- **pyproject.toml**: Updated to v1.0.0
- **Package name**: `cosmos-compiler` → `solvens-core`
- **Entry point**: `cosmos` → `solvens`

### Fixed

- Parser syntax errors in demo workflows
- Lazy imports in CLI for better error handling
- RBAC role permission inheritance
- JWT token generation without external dependency

## [0.4.5] - Previous Release

### Added
- Cosmos DSL compiler v1
- Parser with lexer
- AST nodes and visitor pattern
- Basic CLI

### Known Issues
- No cost safety
- No RBAC
- Limited provider support
- No Docker setup
