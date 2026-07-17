# SOLVENS CORE - Agent Memory

## IMPORTANT CONTEXT

### About Cosmos

**Cosmos is NOT:**
- Cosmos DB (Azure database)
- Apache Cosmos
- Any external technology
- A cloud platform

**Cosmos IS:**
A proprietary computational representation language developed by **Solvens Amoris**.

Cosmos is a language for representing computations based on:
- **AST** (Abstract Syntax Trees)
- **DAG** (Directed Acyclic Graphs)
- **Structural Identity**
- **Canonicalization**
- **Separation of Representation and Execution**
- **Graph Transformation**
- **Visualization Contracts**

### Before Implementing Cosmos Integration

⚠️ **CRITICAL**: Before implementing ANY Cosmos integration:

1. **DO NOT** assume what Cosmos is
2. **DO NOT** create a new Cosmos-like language
3. **DO NOT** use Cosmos DB or any external Cosmos variant

Instead:
1. Study the official Cosmos specification provided by the user
2. Review Cosmos RFCs (RFC-0001, RFC-0002, RFC-0004-F, etc.)
3. Understand COSMOS_SPEC, TRANSFORMATION_RULES, and VIEWER_CONTRACT
4. Respect existing implementation and contracts

### Cosmos Repository

If a Cosmos repository is provided, it should be cloned and analyzed before any changes:

```bash
gh repo clone SolvensAmoris/<cosmos-repo>
```

---

## Project Architecture

### Core Components

| Component | Status | Description |
|-----------|--------|-------------|
| Agent Orchestrator | ✅ Done | Task queuing, parallel execution, priorities |
| Capability Router | ✅ Done | Rule-based provider selection |
| Provider System | ✅ Done | OpenAI, Anthropic, Ollama adapters |
| Plugin Registry | ✅ Done | Dynamic plugin loading |
| REST API | ✅ Done | FastAPI endpoints |
| CLI | ✅ Done | Typer-based commands |
| Docker | ✅ Done | Dockerfile, docker-compose |
| Documentation | ✅ Done | ARCHITECTURE.md, DEPLOYMENT.md |

### Provider Routing Rules

```
Code Generation  → Anthropic (Claude)
Research        → Sakana
Documentation   → Google (Gemini)
Reasoning      → OpenAI (GPT)
Creative       → Grok
Translation     → DeepSeek
Offline        → Ollama
Video          → Pollo AI
```

### Design Patterns

- **SOLID Principles**: Single responsibility, open/closed, etc.
- **Clean Architecture**: Layered separation
- **Hexagonal Architecture**: Ports and adapters
- **Event-Driven**: Async event handling
- **Plugin Architecture**: Zero core modification for extensions

---

## Development Guidelines

### Before Modifying Code

1. Analyze the repository completely
2. Understand the entire architecture
3. Detect existing modules
4. Detect technical debt
5. Detect improvement opportunities
6. Do NOT remove functionality
7. Do NOT break compatibility
8. Do NOT rewrite unnecessarily

### Always Reuse Before Creating

Reuse existing code before creating new implementations.

### Commit Strategy

Make small, descriptive commits:
```
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
refactor: improve code
```

---

## Environment Setup

```bash
# Install dependencies
pip install -e ".[all]"

# Run tests
pytest tests/ -v

# Run CLI
solvens doctor

# Run API
uvicorn solvens.api.main:app
```

---

## Key Files

| File | Purpose |
|------|---------|
| `solvens/core/` | Base classes, types, config |
| `solvens/agents/` | Orchestrator, agent system |
| `solvens/router/` | Capability routing |
| `solvens/providers/` | Provider interfaces |
| `solvens/plugins/` | Provider implementations |
| `solvens/registry/` | Plugin system |
| `docs/` | Architecture, deployment, contributing |

---

## Testing

```bash
# All tests
pytest tests/ -v

# With coverage
pytest --cov=solvens --cov-report=html

# Specific module
pytest tests/unit/test_orchestrator.py -v
```

---

## Contact

- **Author**: Luis Alberto Burciaga Miker
- **Organization**: Solvens Amoris
- **Repository**: github.com/SolvensAmoris/solvens-core
