# SOLVENS CORE - File Index

**Version:** 0.4.5  
**Last Updated:** 2026-07-17

---

## 1. Root Level Files

| Ruta | Descripción | Función |
|------|-------------|---------|
| pyproject.toml | Project configuration | Dependencies, metadata, tools |
| README.md | Project readme | Overview, installation, usage |
| AGENTS.md | Agent memory | Context for AI agents |
| temporal_violation.cosmos | Test file | Cosmos compiler test case |
| valid_cosmos.cosmos | Test file | Valid Cosmos file |
| strassen_recursion_tree.py | Visualization | Strassen algorithm tree visualization |
| optimized_strassen_fft_topological.py | Algorithm | Strassen + FFT optimization |
| strassen_tree.png | Generated | Tree visualization output |

---

## 2. solvens/ - Core Package

### 2.1 Main Package

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/__init__.py | Package init | Version, exports |
| solvens/__main__.py | Entry point | CLI entry |

### 2.2 Agents Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/agents/__init__.py | Module init | Exports |
| solvens/agents/orchestrator.py | Agent Orchestrator | Central execution coordinator |
| solvens/agents/types.py | Agent types | Type definitions |
| solvens/agents/exceptions.py | Agent exceptions | Error classes |

### 2.3 Router Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/router/__init__.py | Module init | Exports |
| solvens/router/capability.py | Capability Router | Task routing to providers |

### 2.4 Events Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/events/__init__.py | Module init | Exports |
| solvens/events/manager.py | Event Manager | Event-driven communication |
| solvens/events/types.py | Event types | Event definitions |

### 2.5 Config Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/config/__init__.py | Module init | Exports |
| solvens/config/settings.py | Settings | Configuration management |

### 2.6 Types Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/types/__init__.py | Module init | Exports |
| solvens/types/messages.py | Message types | Message definitions |

### 2.7 Providers Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/providers/__init__.py | Module init | Exports |
| solvens/providers/base.py | Base Provider | Provider interface |
| solvens/providers/registry.py | Provider Registry | Plugin registration |
| solvens/providers/openai.py | OpenAI Provider | OpenAI adapter |
| solvens/providers/anthropic.py | Anthropic Provider | Anthropic adapter |
| solvens/providers/ollama.py | Ollama Provider | Ollama local adapter |
| solvens/providers/google.py | Google Provider | Google AI adapter |

### 2.8 Cosmos Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/cosmos/__init__.py | Module init | Exports, version |
| solvens/cosmos/ast.py | AST | Abstract Syntax Tree |
| solvens/cosmos/dag.py | DAG | Directed Acyclic Graph |
| solvens/cosmos/parser.py | Parser | DSL/JSON parser |
| solvens/cosmos/canonicalizer.py | Canonicalizer | Deduplication/normalization |
| solvens/cosmos/planner.py | Planner | Execution planning |
| solvens/cosmos/runtime.py | Runtime | Execution coordination |
| solvens/cosmos/executor.py | Executor | SOLVENS CORE integration |
| solvens/cosmos/demo.py | Demo | Integration demo |

### 2.9 API Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/api/__init__.py | Module init | Exports |
| solvens/api/main.py | FastAPI app | REST API entry |
| solvens/api/routes/__init__.py | Routes init | Routes exports |
| solvens/api/routes/chat.py | Chat routes | /api/chat endpoints |
| solvens/api/routes/providers.py | Provider routes | /api/providers endpoints |
| solvens/api/routes/tasks.py | Task routes | /api/tasks endpoints |
| solvens/api/routes/models.py | Model routes | /api/models endpoints |
| solvens/api/routes/status.py | Status routes | /api/status endpoints |

### 2.10 CLI Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/cli/__init__.py | Module init | Exports |
| solvens/cli/main.py | CLI entry | Typer CLI app |
| solvens/cli/commands/__init__.py | Commands init | Commands exports |
| solvens/cli/commands/chat.py | Chat command | solvens chat |
| solvens/cli/commands/doctor.py | Doctor command | solvens doctor |
| solvens/cli/commands/providers.py | Providers command | solvens providers |
| solvens/cli/commands/plugins.py | Plugins command | solvens plugins |
| solvens/cli/commands/models.py | Models command | solvens models |
| solvens/cli/commands/schedule.py | Schedule command | solvens schedule |

### 2.11 Dashboard Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/dashboard/__init__.py | Module init | Exports |
| solvens/dashboard/app.py | Streamlit app | Dashboard entry |
| solvens/dashboard/pages/__init__.py | Pages init | Page exports |
| solvens/dashboard/pages/overview.py | Overview page | Dashboard home |
| solvens/dashboard/pages/agents.py | Agents page | Agent monitoring |
| solvens/dashboard/pages/tasks.py | Tasks page | Task queue |
| solvens/dashboard/pages/providers.py | Providers page | Provider status |

### 2.12 Docker Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/docker/__init__.py | Module init | Exports |
| solvens/docker/build.py | Docker build | Build configuration |

### 2.13 Workflows Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| solvens/workflows/__init__.py | Module init | Exports |
| solvens/workflows/executor.py | Workflow executor | Execute workflows |

---

## 3. cosmos/ - Cosmos Language Package

### 3.1 Main Package

| Ruta | Descripción | Función |
|------|-------------|---------|
| cosmos/__init__.py | Package init | Exports |

### 3.2 Compiler Module

| Ruta | Descripción | Función |
|------|-------------|---------|
| cosmos/compiler/__init__.py | Module init | Exports |
| cosmos/compiler/__main__.py | CLI | Compiler entry point |
| cosmos/compiler/errors.py | Errors | CompileError, InternalCompileError |
| cosmos/compiler/schema.py | Schema | AST schema validation |
| cosmos/compiler/transformer.py | Transformer | Lark to Dict transformation |

### 3.3 Compiler Validators

| Ruta | Descripción | Función |
|------|-------------|---------|
| cosmos/compiler/validators/__init__.py | Module init | Exports |
| cosmos/compiler/validators/temporal.py | Temporal | Temporal restriction verification |

### 3.4 Tests

| Ruta | Descripción | Función |
|------|-------------|---------|
| cosmos/tests/__init__.py | Module init | Exports |
| cosmos/tests/test_kv_state_machine.py | KV tests | KV cache state machine tests |
| cosmos/tests/test_llama_attention.py | Attention tests | LlamaAttention + CACHE_TRANSITION |
| cosmos/tests/test_llama_decoder_layer.py | Layer tests | Decoder layer auditing |
| cosmos/tests/test_llama_full.py | Full tests | End-to-end LLaMA audit |

### 3.5 Docs

| Ruta | Descripción | Función |
|------|-------------|---------|
| cosmos/docs/LLAMA_AUDIT_SPEC.md | LLaMA spec | LLaMA audit specification |

---

## 4. tests/ - Test Suite

| Ruta | Descripción | Función |
|------|-------------|---------|
| tests/__init__.py | Package init | Exports |
| tests/conftest.py | Pytest config | Fixtures |
| tests/unit/__init__.py | Unit init | Exports |
| tests/unit/test_orchestrator.py | Orchestrator tests | Orchestrator unit tests |
| tests/unit/test_router.py | Router tests | Router unit tests |
| tests/unit/test_events.py | Events tests | Event system tests |
| tests/integration/__init__.py | Integration init | Exports |
| tests/integration/test_api.py | API tests | REST API integration tests |

---

## 5. docs/ - Documentation

| Ruta | Descripción | Función |
|------|-------------|---------|
| docs/ARCHITECTURE_REPORT.md | Architecture report | Project analysis |
| docs/MIGRATION_PLAN.md | Migration plan | Migration roadmap |
| docs/COSMOS_ARCHITECTURE.md | Cosmos spec | Cosmos language architecture |

---

## 6. docker/ - Docker Files

| Ruta | Descripción | Función |
|------|-------------|---------|
| docker/Dockerfile | Main Dockerfile | Production image |
| docker/docker-compose.yml | Compose file | Multi-service setup |
| docker/entrypoint.sh | Entrypoint | Container entry |

---

## 7. Configuration Files

| Ruta | Descripción | Función |
|------|-------------|---------|
| .env.example | Environment template | Example variables |
| .gitignore | Git ignore | Excluded patterns |
| pyproject.toml | Project config | Dependencies, tools |
| ruff.toml | Ruff config | Linter settings |
| pytest.ini | Pytest config | Test configuration |

---

## 8. Summary Statistics

| Category | Count |
|---------|-------|
| Python files | ~60 |
| Test files | ~10 |
| Documentation files | ~7 |
| Configuration files | ~5 |
| Docker files | ~3 |
| Cosmos test files | ~2 |
| Total | ~80+ |

---

**End of File Index**
