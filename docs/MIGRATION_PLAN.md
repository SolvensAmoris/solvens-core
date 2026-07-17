# SOLVENS CORE - Migration Plan

**Repository:** https://github.com/SolvensAmoris/solvens-core  
**Version:** 1.0.0  
**Last Updated:** 2025-01-17  

---

## 1. Current State

### Architecture: None
- **Status:** Greenfield Project
- **Codebase:** Empty Repository
- **Modules:** None
- **Documentation:** None

### Environment
- **Python Version:** 3.11+
- **Package Manager:** uv (recommended)
- **Repository:** Fresh clone

---

## 2. Target Architecture

### Final State
```
                     ┌─────────────────┐
                     │   SOLVENS CORE  │
                     │  (AI OS Kernel) │
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

---

## 3. Implementation Phases

### Phase 1: Foundation (Current)
**Duration:** 1-2 weeks  
**Goal:** Core abstractions, Agent Orchestrator, Router

#### Deliverables
- [ ] Core module (base classes, types, config, exceptions)
- [ ] Agent Orchestrator (task execution, coordination)
- [ ] Capability Router (rule-based routing)
- [ ] Basic plugin infrastructure

#### Files to Create
```
core/
├── __init__.py
├── base.py
├── config.py
├── exceptions.py
└── types.py

agents/
├── __init__.py
├── orchestrator.py
├── base.py
└── executor.py

router/
├── __init__.py
├── router.py
└── rules.py
```

---

### Phase 2: Provider System
**Duration:** 2-3 weeks  
**Goal:** Provider interface, adapters, registry

#### Deliverables
- [ ] Provider base interface
- [ ] Provider registry
- [ ] Core provider adapters (OpenAI, Claude, Ollama)
- [ ] Provider configuration management
- [ ] Health checks and fallback

#### Files to Create
```
providers/
├── __init__.py
├── base.py
├── registry.py
├── types.py

plugins/
├── __init__.py
├── openai/
├── anthropic/
└── ollama/

registry/
├── __init__.py
├── plugin.py
├── manager.py
└── loader.py
```

---

### Phase 3: Advanced Components
**Duration:** 2-3 weeks  
**Goal:** Memory, Planner, Scheduler, Events

#### Deliverables
- [ ] Memory layer with multiple backends
- [ ] Task Planner (decomposition)
- [ ] Task Scheduler (queues, workers)
- [ ] Event dispatcher system

#### Files to Create
```
memory/
├── __init__.py
├── base.py
├── sqlite.py
├── redis.py
├── vector.py

planner/
├── __init__.py
├── decomposer.py
├── validator.py

scheduler/
├── __init__.py
├── queue.py
├── priority.py
├── worker.py

events/
├── __init__.py
├── dispatcher.py
├── handlers.py
```

---

### Phase 4: Interface Layer
**Duration:** 2-3 weeks  
**Goal:** REST API, CLI, Dashboard

#### Deliverables
- [ ] FastAPI REST endpoints
- [ ] CLI commands (solvens chat, solvens doctor, etc.)
- [ ] Web Dashboard (Streamlit/Gradio)
- [ ] Docker configuration

#### Files to Create
```
api/
├── __init__.py
├── main.py
├── routes/

cli/
├── __init__.py
├── main.py
├── commands/

dashboard/
├── __init__.py
├── app.py
├── routes/

docker/
├── Dockerfile
├── docker-compose.yml
```

---

## 4. Migration Order

### Step 1: Project Setup
```bash
# Initialize project
git init
cppyproject.toml
poetry init

# Install core dependencies
poetry add fastapi uvicorn pydantic python-dotenv httpx
poetry add --group dev pytest pytest-asyncio pytest-cov
```

### Step 2: Core Module
```bash
# Create core/
touch core/__init__.py
# Implement base abstractions
# Add type definitions
# Set up configuration
```

### Step 3: Agent Orchestrator
```bash
# Create agents/
touch agents/__init__.py
# Implement orchestrator
# Add executor
# Create agent base class
```

### Step 4: Capability Router
```bash
# Create router/
touch router/__init__.py
# Implement routing logic
# Add rule engine
# Configure default rules
```

### Step 5: Plugin System
```bash
# Create registry/
touch registry/__init__.py
# Implement plugin manager
# Add plugin loader
```

### Step 6: Provider Adapters
```bash
# Create providers/
touch providers/__init__.py
# Implement base interface
# Create adapters
```

### Step 7: Memory Layer
```bash
# Create memory/
touch memory/__init__.py
# Implement storage backends
# Add vector support
```

### Step 8: Advanced Components
```bash
# Create planner/, scheduler/, events/
touch planner/__init__.py
touch scheduler/__init__.py
touch events/__init__.py
# Implement remaining features
```

### Step 9: API & CLI
```bash
# Create api/, cli/
touch api/__init__.py
touch cli/__init__.py
# Implement interfaces
```

### Step 10: Docker & Docs
```bash
# Create docker/, docs/
# Add Docker configuration
# Write documentation
```

---

## 5. Compatibility Matrix

| Component | Min Version | Max Version | Status |
|-----------|-------------|-------------|--------|
| Python | 3.11 | 3.13 | Tested |
| FastAPI | 0.109 | Latest | Compatible |
| Pydantic | 2.5 | Latest | Compatible |
| Ollama | 0.1 | Latest | Compatible |

---

## 6. Breaking Changes

### None (Greenfield Project)
No breaking changes as this is a new project.

---

## 7. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Scope creep | High | High | Strict phase gates |
| Provider API changes | Medium | Medium | Abstraction layer |
| Performance issues | Medium | Medium | Benchmarking each phase |
| Integration failures | High | Low | Comprehensive tests |

---

## 8. Success Criteria

### Phase 1 Complete When:
- [ ] `from solvens.core import BaseModel` works
- [ ] `from solvens.agents import Orchestrator` works
- [ ] `from solvens.router import Router` works
- [ ] Basic agent can be created and executed
- [ ] Router can route to different providers

### Phase 2 Complete When:
- [ ] All providers implement same interface
- [ ] Provider can be swapped without code changes
- [ ] Plugins can be loaded dynamically
- [ ] Health checks work for all providers

### Phase 3 Complete When:
- [ ] Memory works with multiple backends
- [ ] Tasks can be decomposed automatically
- [ ] Scheduler handles priority queues
- [ ] Events propagate correctly

### Phase 4 Complete When:
- [ ] REST API returns expected responses
- [ ] CLI commands execute correctly
- [ ] Dashboard displays system status
- [ ] Docker builds and runs successfully

---

## 9. Rollback Plan

### If Phase X Fails:
1. Revert to last working commit
2. Identify failed component
3. Fix within same phase
4. Continue to next phase

### Git Strategy
```bash
# Phase branches
git checkout -b phase-1-foundation
git checkout -b phase-2-providers
git checkout -b phase-3-advanced
git checkout -b phase-4-interface

# Merge to main only when phase is complete
git checkout main
git merge phase-1-foundation
```

---

## 10. Resources

### Team
- **Author:** Luis Alberto Burciaga Miker
- **Contributors:** TBD

### External Dependencies
- OpenAI API
- Anthropic API
- Google AI API
- Ollama (local)
- Docker

### Documentation
- This migration plan
- ARCHITECTURE_REPORT.md
- Per-component README files
- API documentation

---

## 11. Timeline

```
Week 1-2: Phase 1 - Foundation
    ├── Day 1-2: Project setup, core module
    ├── Day 3-5: Agent Orchestrator
    └── Day 6-10: Capability Router

Week 3-5: Phase 2 - Provider System
    ├── Day 11-14: Provider interface, registry
    └── Day 15-21: Provider adapters

Week 6-8: Phase 3 - Advanced Components
    ├── Day 22-28: Memory layer
    ├── Day 29-35: Planner, Scheduler
    └── Day 36-42: Event system

Week 9-11: Phase 4 - Interface Layer
    ├── Day 43-49: REST API
    ├── Day 50-56: CLI
    └── Day 57-63: Dashboard, Docker

Week 12: Polish & Release
    ├── Documentation
    ├── Testing
    └── Release v1.0.0
```

---

**Last Updated:** 2025-01-17  
**Next Review:** After Phase 1 completion
