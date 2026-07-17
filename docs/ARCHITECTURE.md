# SOLVENS CORE - Arquitectura

## Visión General

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOLVENS CORE                             │
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │     CLI     │    │     API     │    │      Dashboard      │  │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘  │
│         │                   │                      │             │
│         └───────────────────┼──────────────────────┘             │
│                             │                                    │
│                      ┌──────▼──────┐                           │
│                      │   cosmos/    │ ◄── SOURCE OF TRUTH      │
│                      │  (core)      │                           │
│                      └──────┬──────┘                           │
│                             │                                    │
│         ┌──────────────────┼──────────────────┐                │
│         │                  │                  │                │
│  ┌──────▼──────┐    ┌──────▼──────┐   ┌──────▼──────┐        │
│  │   parser/   │    │     dag/     │   │  providers/ │        │
│  │  (Lexer,    │    │  (Directed  │   │ (OpenAI,    │        │
│  │   Parser)   │    │   Acyclic   │   │  Ollama)    │        │
│  └─────────────┘    │   Graph)    │   └─────────────┘        │
│                      └─────────────┘                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## SOURCE OF TRUTH

**cosmos/** es el único paquete oficial y fuente de verdad. Todo el código legacy está siendo migrado aquí.

---

# SOLVENS CORE Architecture

**Version:** 0.1.0  
**Author:** Luis Alberto Burciaga Miker

---

## Overview

SOLVENS CORE is an AI Operating System designed to be modular, extensible, and provider-agnostic. It provides a unified interface for working with multiple AI providers while maintaining clean separation of concerns.

## High-Level Architecture

```
в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ
в”Ӯ                         SOLVENS CORE                             в”Ӯ
в”ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Ө
в”Ӯ                                                                  в”Ӯ
в”Ӯ   в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ  в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ  в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ          в”Ӯ
в”Ӯ   в”Ӯ  REST API    в”Ӯ  в”Ӯ    CLI       в”Ӯ  в”Ӯ  Dashboard   в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ  (FastAPI)   в”Ӯ  в”Ӯ   (Typer)    в”Ӯ  в”Ӯ  (Streamlit) в”Ӯ          в”Ӯ
в”Ӯ   в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ  в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ  в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ          в”Ӯ
в”Ӯ          в”Ӯ                 в”Ӯ                 в”Ӯ                   в”Ӯ
в”Ӯ   в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ          в”Ӯ
в”Ӯ   в”Ӯ              Agent Orchestrator                   в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ  - Task Queuing    - Parallel Execution          в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ  - Priority Mgmt   - Retry Logic                 в”Ӯ          в”Ӯ
в”Ӯ   в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ          в”Ӯ
в”Ӯ          в”Ӯ                 в”Ӯ                                      в”Ӯ
в”Ӯ   в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ  в”Ңв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ  в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ          в”Ӯ
в”Ӯ   в”Ӯ   Planner    в”Ӯ  в”Ӯ  Scheduler  в”Ӯ  в”Ӯ   Memory     в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ              в”Ӯ  в”Ӯ             в”Ӯ  в”Ӯ              в”Ӯ          в”Ӯ
в”Ӯ   в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ  в””в”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ  в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ          в”Ӯ
в”Ӯ          в”Ӯ                 в”Ӯ                 в”Ӯ                   в”Ӯ
в”Ӯ   в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ          в”Ӯ
в”Ӯ   в”Ӯ              Capability Router                     в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ  - Rule-based routing                             в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ  - Provider selection                             в”Ӯ          в”Ӯ
в”Ӯ   в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ          в”Ӯ
в”Ӯ          в”Ӯ                                                      в”Ӯ
в”Ӯ   в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ          в”Ӯ
в”Ӯ   в”Ӯ              Plugin Registry                       в”Ӯ          в”Ӯ
в”Ӯ   в”Ӯ  - Dynamic loading    - Lifecycle management     в”Ӯ          в”Ӯ
в”Ӯ   в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ          в”Ӯ
в”Ӯ          в”Ӯ       в”Ӯ               в”Ӯ        в”Ӯ                     в”Ӯ
в”Ӯ   в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв–јв”Җв”җ в”Ңв”Җв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”җ в”Ңв”Җв”Җв”Җв”Җв”Җв–јв”Җв”Җв”Җв”Җв”җ в”Ңв”Җв–јв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ            в”Ӯ
в”Ӯ   в”Ӯ OpenAI в”Ӯ в”ӮAnthropic в”Ӯ в”Ӯ  Ollama  в”Ӯ в”Ӯ Google  в”Ӯ  ...        в”Ӯ
в”Ӯ   в””в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ в””в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ в””в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ в””в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ              в”Ӯ
в”Ӯ                                                                  в”Ӯ
в””в”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”ҳ
```

## Core Components

### 1. Agent Orchestrator

The central coordination system for all agent operations.

**Responsibilities:**
- Task submission and queuing
- Parallel and sequential execution
- Priority management
- Retry logic with exponential backoff
- Task cancellation
- Event hooks for monitoring

**Key Classes:**
- `AgentOrchestrator`: Main coordinator
- `Task`: Represents a unit of work
- `TaskResult`: Result of task execution

### 2. Capability Router

Intelligently routes tasks to optimal providers based on content analysis.

**Routing Logic:**
```
Code Generation  вҶ’ Anthropic (Claude)
Research         вҶ’ Sakana
Documentation    вҶ’ Google (Gemini)
Reasoning        вҶ’ OpenAI (GPT)
Offline/Local    вҶ’ Ollama
Video            вҶ’ Pollo AI
```

**Key Classes:**
- `CapabilityRouter`: Main routing logic
- `RoutingRule`: Defines routing patterns
- `ProviderRegistry`: Manages available providers

### 3. Provider System

Unified interface for AI providers with pluggable adapters.

**Interface:**
```python
class ProviderClient(Protocol):
    async def chat(messages, **options) -> Response
    async def embeddings(texts, **options) -> list[list[float]]
    async def vision(image, prompt, **options) -> Response
    async def health_check() -> bool
```

**Available Providers:**
| Provider | Type | Capabilities |
|----------|------|--------------|
| OpenAI | Cloud | Chat, Embeddings, Function Calling |
| Anthropic | Cloud | Chat, Vision, Streaming |
| Ollama | Local | Chat, Embeddings |
| Google | Cloud | Chat, Vision |
| DeepSeek | Cloud | Chat |

### 4. Plugin System

Extends SOLVENS CORE without modifying core code.

**Key Classes:**
- `PluginManager`: Manages plugin lifecycle
- `Plugin`: Base class for plugins
- `PluginMetadata`: Plugin information

### 5. Memory Layer

Pluggable storage system for agent context.

**Supported Backends:**
- SQLite (default)
- PostgreSQL
- Redis
- Vector DB (ChromaDB)

## Design Patterns

### SOLID Principles
- **S**: Single Responsibility - Each module has one purpose
- **O**: Open/Closed - Extend via plugins, not modification
- **L**: Liskov Substitution - All providers interchangeable
- **I**: Interface Segregation - Small, focused interfaces
- **D**: Dependency Inversion - Depend on abstractions

### Architectural Patterns
- **Clean Architecture**: Layered separation
- **Hexagonal Architecture**: Ports and adapters
- **Event-Driven**: Async event handling
- **Plugin Architecture**: Extensibility

## Data Flow

```
User Request
     в”Ӯ
     в–ј
в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ
в”Ӯ  REST API   в”Ӯ
в”Ӯ  /cli       в”Ӯ
в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”ҳ
       в”Ӯ
       в–ј
в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ
в”Ӯ Orchestratorв”Ӯ
в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”ҳ
       в”Ӯ
       в–ј
в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ
в”Ӯ   Router    в”Ӯв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв–ә Routing Rules
в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”ҳ
       в”Ӯ
       в–ј
в”Ңв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”Җв”җ
в”Ӯ  Provider   в”Ӯ
в””в”Җв”Җв”Җв”Җв”Җв”Җв”¬в”Җв”Җв”Җв”Җв”Җв”Җв”ҳ
       в”Ӯ
       в–ј
   AI Response
```

## Security

- **No API Key Storage**: Keys loaded from environment only
- **Docker Secrets**: Support for secure key management
- **Environment Variables**: All configuration via env vars
- **Isolated Execution**: Plugins run in sandboxed contexts

## Performance

- **Async-First**: All I/O operations are asynchronous
- **Connection Pooling**: HTTP clients reuse connections
- **Caching**: Support for response caching
- **Rate Limiting**: Built-in rate limit handling
- **Batching**: Efficient batch embeddings

## Testing

- **Unit Tests**: 66+ tests covering all components
- **Integration Tests**: Provider API tests
- **Mock Tests**: Isolated component testing

## Deployment

### Docker
```bash
docker-compose -f docker/docker-compose.yml up
```

### Systemd
```bash
cp docker/solvens.service ~/.config/systemd/user/
systemctl --user enable solvens
systemctl --user start solvens
```

### Manual
```bash
pip install -e ".[all]"
uvicorn solvens.api.main:app
```

## Future Enhancements

- Multi-agent collaboration
- Advanced memory retrieval
- Custom routing strategies
- Model fine-tuning integration
- Enterprise SSO
- Audit logging
