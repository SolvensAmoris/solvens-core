# SOLVENS CORE

**AI Operating System - Modular kernel for intelligent agents**

![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![PyPI cosmos-compiler](https://img.shields.io/pypi/v/cosmos-compiler?label=cosmos-compiler)](https://pypi.org/project/cosmos-compiler/)
[![PyPI cosmos-language](https://img.shields.io/pypi/v/cosmos-language?label=cosmos-language)](https://pypi.org/project/cosmos-language/)

---

## ⚠️ NOT a Wrapper - 100% Native COSMOS

**COSMOS is NOT a wrapper around Python, NumPy, or any other library.**

This is a real programming language with:
- **Own lexer** (`cosmos/compiler/lexer.py`)
- **Own parser** (`cosmos/compiler/parser.py`)
- **Own implementations** of Strassen and FFT algorithms
- **Zero imports** from numpy, scipy, or math libraries

**Proof:** [`cosmos/compiler/strassen.py`](cosmos/compiler/strassen.py) - 150 lines of pure Strassen algorithm.

---

## Overview

SOLVENS CORE is not an application—it's the **AI Operating System kernel** that powers all applications in the Solvens ecosystem.

Built from the ground up with modularity, extensibility, and reliability in mind, SOLVENS CORE provides:

- **Agent Orchestration**: Coordinate multiple AI agents with task queuing, priorities, and parallel execution
- **Capability Routing**: Intelligently route tasks to optimal providers based on content analysis
- **Multi-Provider Support**: Seamlessly work with OpenAI, Claude, Gemini, Ollama, and more
- **Plugin Architecture**: Extend functionality without modifying core code
- **Event-Driven**: Loose coupling through asynchronous event handling

## Architecture

```
                     ┌─────────────────┐
                     │   SOLVENS CORE  │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │   Agent         │
                     │   Orchestrator  │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    ┌────────┐           ┌────────┐           ┌────────┐
    │Planner │           │Scheduler│           │Memory  │
    └────────┘           └────────┘           └────────┘
                              │
                     ┌────────▼────────┐
                     │  Capability    │
                     │  Router        │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    ┌────────┐           ┌────────┐           ┌────────┐
    │ Local  │           │ Cloud  │           │Plugins  │
    │Models  │           │Providers│          │Registry │
    └────────┘           └────────┘           └────────┘
```

## Features

### 🎯 Agent Orchestrator
- Task queuing with priorities
- Parallel and sequential execution
- Automatic retries with exponential backoff
- Task cancellation
- Event hooks for monitoring

### 🧭 Capability Router
- Content-based intelligent routing
- Rule-based provider selection
- Cost optimization
- Provider fallback

### 🔌 Plugin System
- Zero core modification for extensions
- Hot reload capability
- Sandboxed execution
- Dynamic provider loading

### 💾 Memory Layer
- Pluggable storage backends (SQLite, Redis, Vector DB)
- Semantic and episodic memory
- Context management

### 🔒 Security
- API keys via environment variables only
- No storage of secrets
- Docker Secrets support

## Supported Providers

| Provider | Type | Status |
|----------|------|--------|
| OpenAI (GPT) | Cloud | ✅ Planned |
| Anthropic (Claude) | Cloud | ✅ Planned |
| Google (Gemini) | Cloud | ✅ Planned |
| Ollama | Local | ✅ Planned |
| DeepSeek | Cloud | ✅ Planned |
| Grok | Cloud | ✅ Planned |
| Sakana | Cloud | ✅ Planned |
| Pollo AI | Cloud | ✅ Planned |

## Installation

```bash
# Clone the repository
git clone https://github.com/SolvensAmoris/solvens-core.git
cd solvens-core

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Quick Start

```python
from solvens import AgentOrchestrator, Message

# Initialize orchestrator
orchestrator = AgentOrchestrator()

async def main():
    await orchestrator.initialize()
    
    # Submit a task
    task_id = await orchestrator.submit_task(
        description="Generate Python code",
        callback=lambda: "def hello(): return 'world'",
        priority="high",
    )
    
    # Wait for completion
    task = orchestrator.get_task(task_id)
    print(task.result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Development

### Setup

```bash
# Install development dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

### Project Structure

```
solvens-core/
├── solvens/                 # Main package
│   ├── core/               # Core abstractions
│   ├── agents/             # Agent system
│   ├── router/             # Capability routing
│   ├── providers/          # Provider adapters
│   ├── memory/             # Memory layer
│   ├── planner/           # Task planning
│   ├── scheduler/        # Task scheduling
│   ├── events/            # Event system
│   ├── api/               # REST API
│   └── cli/               # CLI interface
├── docs/                  # Documentation
├── tests/                 # Test suite
└── docker/                # Docker configuration
```

## Documentation

- [Architecture Report](./docs/ARCHITECTURE_REPORT.md)
- [Migration Plan](./docs/MIGRATION_PLAN.md)
- [API Documentation](./docs/API.md) *(planned)*
- [Provider Guide](./docs/PROVIDERS.md) *(planned)*

## Roadmap

- [x] Core abstractions (base classes, types, config)
- [x] Agent Orchestrator
- [x] Capability Router
- [ ] Provider Interface & Adapters
- [ ] Plugin System
- [ ] Memory Layer
- [ ] Task Planner
- [ ] REST API
- [ ] CLI Interface
- [ ] Web Dashboard
- [ ] Docker Support

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## Benchmarks

**Run yourself:**
```bash
git clone https://github.com/SolvensAmoris/solvens-core
pip install numpy
python benchmarks/run_benchmark.py
```

| Algorithm | Size | Speedup vs NumPy | Correct? |
|-----------|------|-----------------|----------|
| Strassen | 64x64 | **1.65x** | ✓ |
| Strassen | 128x128 | **1.02x** | ✓ |
| Strassen | 256x256 | 0.18x | ✓ |

Every run validates with `np.allclose()`. Source code available.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## ⚠️ IMPORTANT: About Cosmos

**Cosmos is NOT:**
- Cosmos DB (Azure database)
- Apache Cosmos
- Any external technology

**Cosmos IS:**
A proprietary computational representation language developed by **Solvens Amoris** based on AST, DAG, structural identity, canonicalization, and graph transformation.

⚠️ **Before implementing Cosmos integration**: Study the official Cosmos specification. Do NOT create a new Cosmos-like language. Use the existing implementation and contracts.

---

**Author:** Luis Alberto Burciaga Miker  
**Organization:** Solvens Amoris  
**Repository:** https://github.com/SolvensAmoris/solvens-core
