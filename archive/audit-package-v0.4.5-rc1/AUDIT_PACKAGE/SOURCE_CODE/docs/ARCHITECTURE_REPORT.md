# SOLVENS CORE - Architecture Report

**Repository:** https://github.com/SolvensAmoris/solvens-core  
**Organization:** Solvens Amoris  
**Author:** Luis Alberto Burciaga Miker  
**Date:** 2025-01-17  
**Version:** 1.0.0  

---

## 1. Project Overview

### Current State
**Status:** Greenfield Project - Empty Repository  
**Initial Commit:** N/A (New project)  
**Existing Modules:** None  

### Project Mission
SOLVENS CORE is not an application—it is the core kernel that ALL applications in the Solvens ecosystem will use. It must become a modular operating system for intelligent AI agents.

### Target Platforms
- Linux
- Docker
- Local execution
- Cloud deployment
- API
- CLI
- Web Dashboard

### Supported Models
- **Local Models:** Ollama, LM Studio, llama.cpp
- **Cloud Providers:** OpenAI, Claude, Gemini, DeepSeek, Grok, Sakana, Pollo AI

---

## 2. Architecture Blueprint

### High-Level Architecture

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
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                     ┌────────▼────────┐
                     │  Capability      │
                     │  Router          │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    ┌────────┐           ┌────────┐           ┌────────┐
    │ Local  │           │ Cloud  │           │Plugins  │
    │Models  │           │Providers│          │Registry │
    └────────┘           └────────┘           └────────┘
        │                     │                     │
        ▼                     ▼                     ▼
    ┌────────┐           ┌────────┐           ┌────────┐
    │Ollama  │           │GPT     │           │Custom  │
    │LM Studio│          │Claude  │           │Providers│
    │llama.cpp│          │Gemini  │           │        │
    └────────┘           │DeepSeek│           └────────┘
                         │Grok    │
                         │Sakana  │
                         │Pollo AI│
                         └────────┘
```

---

## 3. Directory Structure

```
solvens-core/
├── core/                    # Core kernel and base classes
│   ├── __init__.py
│   ├── base.py             # Base abstractions
│   ├── config.py           # Configuration management
│   ├── exceptions.py       # Custom exceptions
│   └── types.py            # Type definitions
│
├── agents/                  # Agent system
│   ├── __init__.py
│   ├── orchestrator.py     # Main orchestrator
│   ├── base.py             # Base agent class
│   ├── executor.py         # Agent execution
│   └── types.py            # Agent types
│
├── planner/                 # Task planning
│   ├── __init__.py
│   ├── decomposer.py        # Task decomposition
│   ├── validator.py         # Plan validation
│   └── optimizer.py         # Plan optimization
│
├── scheduler/               # Task scheduling
│   ├── __init__.py
│   ├── queue.py            # Task queues
│   ├── priority.py         # Priority management
│   └── worker.py           # Worker management
│
├── memory/                  # Memory management
│   ├── __init__.py
│   ├── base.py             # Memory interface
│   ├── vector.py           # Vector storage
│   ├── episodic.py         # Episodic memory
│   └── semantic.py         # Semantic memory
│
├── router/                  # Capability routing
│   ├── __init__.py
│   ├── router.py           # Main router
│   ├── rules.py           # Routing rules
│   └── selectors.py        # Provider selection
│
├── providers/               # AI providers base
│   ├── __init__.py
│   ├── base.py             # Provider interface
│   ├── registry.py         # Provider registry
│   └── types.py            # Provider types
│
├── registry/                # Plugin registry
│   ├── __init__.py
│   ├── plugin.py           # Plugin base class
│   ├── manager.py          # Plugin manager
│   └── loader.py           # Plugin loader
│
├── plugins/                 # Provider plugins
│   ├── __init__.py
│   ├── openai/
│   ├── anthropic/
│   ├── google/
│   ├── ollama/
│   ├── deepseek/
│   ├── grok/
│   ├── sakana/
│   └── pollo_ai/
│
├── workflows/               # Workflow management
│   ├── __init__.py
│   ├── engine.py           # Workflow engine
│   ├── parser.py           # Workflow parser
│   └── templates/          # Predefined templates
│
├── events/                  # Event system
│   ├── __init__.py
│   ├── dispatcher.py       # Event dispatcher
│   ├── handlers.py         # Event handlers
│   └── types.py            # Event types
│
├── dashboard/              # Web dashboard
│   ├── __init__.py
│   ├── app.py              # Dashboard app
│   ├── routes.py           # Dashboard routes
│   └── templates/          # HTML templates
│
├── api/                    # REST API
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── routes/
│   │   ├── chat.py
│   │   ├── providers.py
│   │   ├── tasks.py
│   │   ├── workflows.py
│   │   ├── models.py
│   │   └── status.py
│   └── middleware/
│
├── cli/                    # CLI interface
│   ├── __init__.py
│   ├── main.py             # CLI entry point
│   ├── commands/
│   │   ├── chat.py
│   │   ├── doctor.py
│   │   ├── providers.py
│   │   ├── workflow.py
│   │   ├── plugins.py
│   │   ├── models.py
│   │   └── schedule.py
│   └── formatter.py        # Output formatting
│
├── docker/                 # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
│
├── config/                 # Configuration files
│   ├── default.yaml
│   ├── production.yaml
│   └── development.yaml
│
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── PROVIDERS.md
│   ├── PLUGINS.md
│   ├── DEPLOYMENT.md
│   ├── CONTRIBUTING.md
│   └── ROADMAP.md
│
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── pyproject.toml          # Python project config
├── README.md               # Main documentation
├── LICENSE                 # License
├── .gitignore
└── Makefile
```

---

## 4. Core Components Analysis

### 4.1 Agent Orchestrator
**Purpose:** Central coordination for all agent operations  
**Responsibilities:**
- Execute agents in parallel or sequential mode
- Coordinate multiple agents
- Manage task queues with priorities
- Cancel tasks on demand
- Implement retry mechanisms with exponential backoff
- Recover from failures

**Strengths:**
- Centralized control
- Built-in parallelism
- Extensible retry logic

**Dependencies:** planner, scheduler, memory

### 4.2 Planner
**Purpose:** Automatically decompose large tasks into subtasks  
**Responsibilities:**
- Break complex tasks into smaller units
- Determine task dependencies
- Optimize execution order
- Validate task decomposition

**Strengths:**
- Autonomous decomposition
- Dependency tracking

**Dependencies:** router, memory

### 4.3 Scheduler
**Purpose:** Manage task execution order and resources  
**Responsibilities:**
- Queue management (FIFO, priority, deadline)
- Worker pool management
- Load balancing
- Resource allocation

**Strengths:**
- Multiple queue strategies
- Efficient resource utilization

**Dependencies:** events, memory

### 4.4 Memory
**Purpose:** Decoupled storage layer for all agent data  
**Responsibilities:**
- Abstract storage interfaces
- Support multiple backends (SQLite, PostgreSQL, Redis, Vector DB)
- Semantic and episodic memory
- Context management

**Strengths:**
- Backend agnostic
- Pluggable storage engines
- Vector similarity search

**Dependencies:** None (core module)

### 4.5 Capability Router
**Purpose:** Intelligently route tasks to optimal providers  
**Responsibilities:**
- Analyze task requirements
- Match capabilities to providers
- Load balancing across providers
- Cost optimization
- Fallback routing

**Routing Logic:**
```
Code → Claude
Research → Sakana
Documentation → Gemini
Reasoning → GPT
Offline → Ollama
Video → Pollo AI
```

**Strengths:**
- Intelligent routing
- Cost awareness
- Provider agnostic

**Dependencies:** providers, registry

### 4.6 Provider Interface
**Purpose:** Unified interface for all AI providers  
**Methods:**
```python
class Provider(Protocol):
    async def chat(messages, **kwargs) -> Response
    async def embeddings(text, **kwargs) -> List[float]
    async def vision(image, prompt, **kwargs) -> Response
    async def speech(audio, **kwargs) -> Response
    async def image(prompt, **kwargs) -> Image
    async def video(prompt, **kwargs) -> Video
```

**Strengths:**
- Provider agnostic
- Easy to add new providers

**Dependencies:** core

### 4.7 Plugin System
**Purpose:** Extend functionality without modifying core  
**Responsibilities:**
- Dynamic plugin loading
- Plugin lifecycle management
- Dependency resolution
- Isolation and sandboxing

**Strengths:**
- Zero core modification for extensions
- Hot reload capability
- Sandboxed execution

**Dependencies:** registry

---

## 5. Design Patterns Applied

### 5.1 SOLID Principles
- **S:** Single Responsibility - Each module has one purpose
- **O:** Open/Closed - Extend via plugins, not modification
- **L:** Liskov Substitution - All providers interchangeable
- **I:** Interface Segregation - Small, focused interfaces
- **D:** Dependency Inversion - Depend on abstractions

### 5.2 Architectural Patterns
- **Clean Architecture:** Layered separation of concerns
- **Hexagonal Architecture:** Ports and adapters
- **Dependency Injection:** Injected dependencies
- **Event-Driven Architecture:** Async event handling
- **Plugin Architecture:** Extensibility without core changes

---

## 6. Strengths & Opportunities

### Strengths
1. **Modular Design:** Easy to maintain and extend
2. **Multi-Provider Support:** No vendor lock-in
3. **Event-Driven:** Loose coupling via events
4. **Plugin System:** Infinite extensibility
5. **Type Safety:** Full type annotations
6. **Async-First:** Modern Python async/await

### Opportunities
1. **Ecosystem Growth:** Cosmos, AMOX, Pollo AI Editor integration
2. **Enterprise Features:** SSO, audit logs, compliance
3. **Performance Optimization:** Caching, batching, streaming
4. **MLOps Integration:** Model versioning, A/B testing
5. **Multi-Tenancy:** Shared infrastructure for multiple users

---

## 7. Technical Debt Assessment

### Initial State: None (Greenfield)
No existing technical debt to address.

### Future Debt Tracking
Will track and document as the project evolves.

---

## 8. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Provider API changes | High | Medium | Abstract interface, version pinning |
| Performance bottlenecks | Medium | Medium | Profiling, caching, optimization |
| Security vulnerabilities | High | Low | Security audits, dependency scanning |
| Plugin conflicts | Medium | Low | Sandboxed execution, dependency resolution |

---

## 9. Recommendations

### Phase 1: Foundation
1. Implement core abstractions (base.py, types.py)
2. Build Agent Orchestrator with basic task execution
3. Create Capability Router with rule-based routing
4. Establish plugin system foundation

### Phase 2: Providers
1. Implement Provider interface
2. Create adapters for primary providers (OpenAI, Claude, Ollama)
3. Build provider registry and configuration
4. Add health checks and fallback mechanisms

### Phase 3: Advanced Features
1. Implement Memory layer with pluggable backends
2. Build Planner for task decomposition
3. Create Scheduler with priority queues
4. Add event system for async communication

### Phase 4: Interface Layer
1. Build REST API with FastAPI
2. Create CLI with Click/Typer
3. Develop Web Dashboard
4. Add Docker support

---

## 10. Dependencies

### Python Packages
```
# Core
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
python-dotenv>=1.0.0
httpx>=0.26.0

# CLI
typer>=0.12.0
rich>=13.7.0

# Storage
sqlalchemy>=2.0.0
redis>=5.0.0
pgvector>=0.2.0
chromadb>=0.4.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
httpx>=0.26.0

# Utils
tenacity>=8.2.0
structlog>=24.1.0
```

---

## 11. Conclusion

SOLVENS CORE will be built as a professional-grade AI agent operating system with:

- **Modularity:** Every component is independently replaceable
- **Extensibility:** New providers via plugins, no core changes
- **Reliability:** Built-in retry, fallback, and recovery
- **Performance:** Async-first, efficient resource utilization
- **Security:** No API key storage, environment-based secrets
- **Usability:** API, CLI, and Dashboard interfaces

The architecture follows industry best practices and will evolve with the ecosystem needs.

---

**Next Step:** Proceed to MIGRATION_PLAN.md for implementation roadmap.
