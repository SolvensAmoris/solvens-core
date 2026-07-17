# Changelog

All notable changes to SOLVENS CORE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
