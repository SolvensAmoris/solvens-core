# SOLVENS CORE - Architecture Document

**Version:** 0.4.5  
**Author:** Luis Alberto Burciaga Miker  
**Last Updated:** 2026-07-17

---

## 1. System Purpose

SOLVENS CORE is an AI Operating System that serves as the core engine for all applications in the Solvens ecosystem. It must function across multiple platforms and execution modes:

- Linux
- Docker
- Local
- Cloud
- API
- CLI
- Dashboard Web

The system supports both local models and cloud providers, with a design principle of never depending on a specific provider.

---

## 2. Execution Flow

### 2.1 Main Pipeline

```
User Input
    │
    ▼
Cosmos Parser
    │
    ▼
Cosmos AST (Abstract Syntax Tree)
    │
    ▼
Cosmos Canonicalizer
    │
    ▼
Cosmos DAG (Directed Acyclic Graph)
    │
    ▼
Cosmos Planner
    │
    ▼
Cosmos Runtime
    │
    ▼
Agent Orchestrator
    │
    ▼
Capability Router
    │
    ▼
Providers (OpenAI, Anthropic, Ollama, etc.)
```

### 2.2 LLaMA Audit Pipeline

```
BatchNorm2D
    │
    ▼
MODEL_STATE
    │
    ▼
LSTM
    │
    ▼
RUNTIME_STATE
    │
    ▼
KV CACHE
    │
    ▼
TRANSFORMER BLOCK
    │
    ▼
LlamaDecoderLayer
    │
    ▼
LlamaModel
    │
    ▼
LlamaForCausalLM
```

---

## 3. Main Components

### 3.1 Core Components

| Component | Path | Description |
|-----------|------|-------------|
| Agent Orchestrator | `solvens/agents/orchestrator.py` | Central execution coordinator |
| Capability Router | `solvens/router/` | Routes tasks to appropriate providers |
| Event System | `solvens/events/` | Event-driven communication |
| Configuration | `solvens/config/` | System configuration management |

### 3.2 Cosmos Language Components

| Component | Path | Description |
|-----------|------|-------------|
| AST | `solvens/cosmos/ast.py` | Abstract Syntax Tree with structural identity |
| DAG | `solvens/cosmos/dag.py` | Directed Acyclic Graph for execution |
| Parser | `solvens/cosmos/parser.py` | DSL/JSON/Natural language parser |
| Canonicalizer | `solvens/cosmos/canonicalizer.py` | Deduplication and normalization |
| Planner | `solvens/cosmos/planner.py` | Execution planning |
| Runtime | `solvens/cosmos/runtime.py` | Execution coordination |
| Executor | `solvens/cosmos/executor.py` | SOLVENS CORE integration |

### 3.3 Cosmos Compiler Components

| Component | Path | Description |
|-----------|------|-------------|
| Errors | `cosmos/compiler/errors.py` | CompileError, InternalCompileError |
| Schema | `cosmos/compiler/schema.py` | AST schema validation |
| Transformer | `cosmos/compiler/transformer.py` | Lark to Dict transformation |
| Temporal Validator | `cosmos/compiler/validators/temporal.py` | Temporal restriction verification |
| CLI | `cosmos/compiler/__main__.py` | Compiler CLI |

### 3.4 LLaMA Audit Components

| Component | Path | Description |
|-----------|------|-------------|
| KV State Machine | `cosmos/tests/test_kv_state_machine.py` | KV cache state transitions |
| LlamaAttention | `cosmos/tests/test_llama_attention.py` | Attention layer + CACHE_TRANSITION |
| DecoderLayer | `cosmos/tests/test_llama_decoder_layer.py` | Decoder layer auditing |
| Full Audit | `cosmos/tests/test_llama_full.py` | End-to-end LLaMA auditing |

### 3.5 Provider System

| Component | Path | Description |
|-----------|------|-------------|
| Registry | `solvens/providers/registry.py` | Plugin registration system |
| Base Provider | `solvens/providers/base.py` | Provider interface |
| OpenAI | `solvens/providers/openai.py` | OpenAI adapter |
| Anthropic | `solvens/providers/anthropic.py` | Anthropic adapter |
| Ollama | `solvens/providers/ollama.py` | Ollama local adapter |

### 3.6 API & CLI

| Component | Path | Description |
|-----------|------|-------------|
| REST API | `solvens/api/` | FastAPI REST endpoints |
| CLI | `solvens/cli/` | Typer CLI commands |
| Dashboard | `solvens/dashboard/` | Streamlit web dashboard |

---

## 4. Module Relationships

### 4.1 Core Dependencies

```
agents/
├── orchestrator.py
│   ├── Uses: events, router, config
│   └── Called by: api, cli, dashboard
│
router/
├── capability.py
│   ├── Uses: registry
│   └── Called by: orchestrator
│
events/
├── manager.py
│   └── Used by: orchestrator, all modules
│
config/
├── settings.py
│   └── Used by: all modules
```

### 4.2 Cosmos Dependencies

```
cosmos/
├── __init__.py
├── ast.py (base types)
├── dag.py (uses ast.py)
├── parser.py (uses ast.py)
├── canonicalizer.py (uses ast.py)
├── planner.py (uses ast.py, dag.py)
├── runtime.py (uses dag.py, planner.py)
├── executor.py (uses runtime.py)
└── demo.py
```

### 4.3 Compiler Dependencies

```
cosmos/compiler/
├── __main__.py
├── errors.py
├── schema.py (uses errors.py)
├── transformer.py (uses errors.py)
└── validators/
    ├── __init__.py
    └── temporal.py (uses errors.py)
```

### 4.4 LLaMA Audit Dependencies

```
cosmos/tests/
├── test_kv_state_machine.py (standalone)
├── test_llama_attention.py (standalone)
├── test_llama_decoder_layer.py (standalone)
└── test_llama_full.py (standalone)
```

---

## 5. Architectural Decisions

### 5.1 Plugin Architecture

All providers are implemented as plugins. The core system never needs modification to add new providers.

```
Provider Interface (base.py)
    │
    ├── OpenAI Plugin
    ├── Anthropic Plugin
    ├── Ollama Plugin
    └── Future Plugins...
```

### 5.2 Event-Driven Architecture

Modules communicate through an event system for loose coupling.

### 5.3 Dependency Injection

All dependencies are injected through constructors, enabling easy testing and swapping of implementations.

### 5.4 SRI-W v0.4.3.2

The Structural Retention Index for Weights:

```python
SRI-W = 0.45·F_content + 0.30·F_position + 0.25·F_quantization
```

Where:
- F_content: Value fidelity (cosine/correlation)
- F_position: Positional integrity (RoPE)
- F_quantization: Post-compression fidelity

---

## 6. Data Flow Examples

### 6.1 Task Execution

1. User sends request via API/CLI/Dashboard
2. Request parsed by Cosmos Parser
3. AST created and canonicalized
4. DAG built for dependency analysis
5. Planner generates execution phases
6. Runtime coordinates execution
7. Capability Router selects provider
8. Provider executes task
9. Results returned through chain

### 6.2 LLaMA KV Cache Audit

1. Cache transition occurs (extend/rollback/evict)
2. CACHE_TRANSITION node generated
3. SRI-W computed before and after
4. Validator checks rules:
   - Append-only (with valid reason)
   - Chunk size (for prefill)
   - Delta SRI-W >= 0
   - Token preservation
5. Report generated

---

## 7. Testing Strategy

### 7.1 Unit Tests

Located in `tests/` directories for each module.

### 7.2 Integration Tests

- `cosmos/tests/test_llama_full.py`: End-to-end LLaMA auditing

### 7.3 Test Results

```
cosmos/tests/
├── test_kv_state_machine.py:     9 passed
├── test_llama_attention.py:       7 passed
├── test_llama_decoder_layer.py:   5 passed
└── test_llama_full.py:            9 passed

Total: 30 passed
```

---

## 8. Security Considerations

### 8.1 API Keys

Never stored in code. Uses:
- .env files
- Docker Secrets
- Environment variables

### 8.2 Secrets Management

All secrets injected at runtime, never committed to repository.

---

## 9. Deployment Options

### 9.1 Docker

```bash
docker build -t solvens-core .
docker run solvens-core
```

### 9.2 Systemd

```bash
sudo cp solvens.service /etc/systemd/system/
sudo systemctl enable solvens
sudo systemctl start solvens
```

### 9.3 Direct Execution

```bash
python -m solvens
solvens chat "Your prompt"
```

---

## 10. Future Enhancements

- Natural language parser improvements
- Real tensor validation for LLaMA audit
- Cosine similarity computation for F_content
- RoPE angle verification for F_position
- vLLM PagedAttention integration
- Streaming inference support

---

**End of Architecture Document**
