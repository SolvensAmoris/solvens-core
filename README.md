# SOLVENS CORE

**AI Agent Orchestration Platform**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/SolvensAmoris/solvens-core)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-orange.svg)](LICENSE)

## Overview

SOLVENS CORE is the nucleus that ALL applications in the Solvens ecosystem will use. It must become an operating system for intelligent agents.

### Features

- **Cosmos DSL**: Domain-specific language for AI workflow definition
- **DAG Execution**: Parallel execution with dependency management
- **Multi-Provider**: OpenAI, Anthropic, Ollama, and more
- **Cost Safety**: Circuit breaker, budgets, rate limiting
- **RBAC**: 6 roles, scoped API keys, audit logging
- **CLI**: Professional command-line interface
- **Docker**: Production-ready containers

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/SolvensAmoris/solvens-core
cd solvens-core

# Install
pip install -e .

# Check version
solvens version
```

### Basic Usage

```bash
# Initialize project
solvens init --name demo

# Compile workflow
solvens compile demo/demo.cosmos

# Validate
solvens validate demo/demo.cosmos

# Simulate (no cost)
solvens simulate demo.cosmos

# Check system
solvens doctor
```

## Docker

```bash
# Build and run
docker build -t solvens .
docker run solvens doctor

# Full stack with docker-compose
docker-compose up

# With Ollama for local inference
docker-compose --profile ollama up
```

## Architecture

```
                 SOLVENS CORE
                       │
              Agent Orchestrator
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Planner         Scheduler       Memory
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              Capability Router
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  Local Models    Cloud Providers    Plugins
        │              │
        │       ┌───────┼───────┐
        ▼       ▼       ▼       ▼
     Ollama    GPT   Claude   Gemini
```

## Documentation

- [Project notes and release checklist](docs/project/)
- [Historical audit reports](docs/audits/)
- [Examples and demos](examples/demos/)
- [Archived audit snapshot](archive/audit-package-v0.4.5-rc1/)

- [CLI Reference](docs/CLI.md)
- [API Documentation](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)

## Tests

```bash
# Run all tests
pytest tests/ -v

# Run integration tests
pytest tests/test_integration.py -v
```

## License

Apache 2.0

**Author:** Luis Alberto Burciaga Miker  
**Co-authored-by:** OpenHands <openhands@all-hands.dev>  
**GitHub:** https://github.com/SolvensAmoris/solvens-core
