# SOLVENS CORE - Core Implementation Plan
## Planner + Scheduler + Executor

**Fecha:** 2025-01-17  
**Estado:** PENDIENTE DE APROBACIÓN  
**Estimación:** 3-4 semanas

---

# RESUMEN EJECUTIVO

El proyecto tiene dos orquestadores existentes pero les falta:
1. **Planner**: No existe para dividir tareas complejas
2. **Scheduler mejorado**: El actual no maneja dependencias DAG
3. **Executor integrado**: Conectar plan → scheduler → executor

**Objetivo:** Crear el flujo completo: `Tarea Compleja → Plan DAG → Ejecución → Resultado`

---

# ANÁLISIS DEL ESTADO ACTUAL

## Lo que EXISTE

| Componente | Ubicación | Estado |
|------------|-----------|--------|
| RuntimeOrchestrator | `solvens/runtime/orchestrator.py` | ✅ Priority queue, async, plugins |
| AgentOrchestrator | `solvens/agents/orchestrator.py` | ✅ Más completo |
| AgentExecutor | `solvens/agents/executor.py` | ✅ Retry, timeout, batch |
| DAG | `cosmos/dag/__init__.py` | ✅ Topological sort, cycle detection |
| SmartRouter | `cosmos/router/smart_router.py` | ✅ Task → Provider routing |
| Cosmos Parser | `cosmos/parser/` | ✅ DSL parsing |
| AST | `cosmos/ast/` | ✅ Definiciones |

## Lo que FALTA

| Componente | Ubicación | Estado |
|------------|-----------|--------|
| **Planner** | `cosmos/planner/` | ❌ NO EXISTE |
| **Scheduler DAG-aware** | `cosmos/scheduler/` | ❌ NO EXISTE |
| **Plan Executor** | `cosmos/executor/` | ❌ NO EXISTE |
| **Task Dependencies** | - | ❌ No hay modelo de dependencia |

---

# ARQUITECTURA PROPUESTA

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                             │
│                    "Research and summarize                      │
│                     coffee providers in Mexico"                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PLANNER                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ LLM Analysis + Cosmos DSL Generation                     │   │
│  │                                                         │   │
│  │ Input: Natural language task                            │   │
│  │ Output: Plan (DAG of Steps with dependencies)           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PLAN RESULT                                  │
│                                                                 │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│  │ Step 1   │────▶│ Step 2   │────▶│ Step 3   │              │
│  │ Research │     │ Analyze  │     │ Summarize│              │
│  └──────────┘     └──────────┘     └──────────┘              │
│                                                                 │
│  DAG: Step1 → Step2 → Step3                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SCHEDULER                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DAG-aware Task Scheduler                                 │   │
│  │                                                         │   │
│  │ - Detect ready tasks (dependencies satisfied)           │   │
│  │ - Execute ready tasks in parallel                       │   │
│  │ - Handle retries, priorities, human-in-the-loop         │   │
│  │ - Emit execution events                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EXECUTOR                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Step Executor                                           │   │
│  │                                                         │   │
│  │ - Execute step with provider                            │   │
│  │ - Tool execution                                       │   │
│  │ - Error handling                                       │   │
│  │ - Result propagation to dependent steps                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       EXECUTION RESULT                          │
│                                                                 │
│  - Completed DAG visualization                                  │
│  - Step results                                                │
│  - Cost and latency metrics                                     │
│  - Audit trail                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# COMPONENTES A CREAR

## 1. PLANNER (`cosmos/planner/`)

### Archivos a crear:

```
cosmos/planner/
├── __init__.py              # Exports públicos
├── types.py                 # Plan, Step, Dependency, PlanStatus
├── llm_planner.py           # LLM-based planner
├── cosmos_planner.py         # Cosmos DSL-based planner
└── tests/
    ├── __init__.py
    └── test_planner.py
```

### Interfaces clave:

```python
@dataclass
class Step:
    id: str
    name: str
    description: str
    provider: ProviderType
    prompt: str
    tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Step IDs
    timeout: float = 60.0
    retry: int = 3

@dataclass
class Plan:
    id: str
    task: str  # Original task description
    steps: list[Step]
    dag: DAG  # Computed from steps
    status: PlanStatus
    metadata: dict = field(default_factory=dict)

class Planner(ABC):
    async def create_plan(self, task: str) -> Plan:
        """Create execution plan from task description."""
        pass
```

---

## 2. SCHEDULER (`cosmos/scheduler/`)

### Archivos a crear:

```
cosmos/scheduler/
├── __init__.py              # Exports públicos
├── types.py                 # ScheduledTask, ScheduleDecision
├── dag_scheduler.py         # DAG-aware scheduler
├── task_queue.py            # Priority queue con dependencias
├── human_in_loop.py         # Human approval hooks
└── tests/
    ├── __init__.py
    └── test_scheduler.py
```

### Interfaces clave:

```python
@dataclass
class ScheduledTask:
    step: Step
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class DAGScheduler:
    """Schedules tasks based on DAG dependencies."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def schedule(self, plan: Plan) -> AsyncGenerator[ScheduledTask, None]:
        """Schedule and yield tasks as they become ready."""
        pass
    
    def get_ready_steps(self) -> list[Step]:
        """Get steps whose dependencies are satisfied."""
        pass
    
    def is_step_ready(self, step: Step) -> bool:
        """Check if a step's dependencies are completed."""
        pass
```

---

## 3. EXECUTOR (`cosmos/executor/`)

### Archivos a crear:

```
cosmos/executor/
├── __init__.py              # Exports públicos
├── types.py                 # ExecutionContext, StepResult
├── step_executor.py         # Execute individual steps
├── tool_registry.py         # Tool registration and execution
├── context_manager.py        # Shared context between steps
├── error_handler.py          # Error classification and recovery
└── tests/
    ├── __init__.py
    └── test_executor.py
```

### Interfaces clave:

```python
@dataclass
class StepResult:
    step_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    cost: float = 0.0
    tokens_used: int = 0
    duration_ms: float = 0.0

class ExecutionContext:
    """Shared context passed between steps."""
    plan_id: str
    step_results: dict[str, StepResult]
    shared_state: dict[str, Any]
    audit_log: list[AuditEntry]

class StepExecutor:
    """Executes individual steps."""
    
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_registry: ToolRegistry,
    ):
        self.providers = provider_registry
        self.tools = tool_registry
    
    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute a single step with given context."""
        pass
```

---

# INTEGRACIÓN CON COMPONENTES EXISTENTES

## Provider Registry

```python
# Usar el existente en cosmos/router/smart_router.py
from cosmos.router.smart_router import ProviderRegistry, Provider

# O crear uno específico para executor
class ExecutorProviderRegistry:
    def get_provider(self, provider_type: ProviderType) -> Provider:
        pass
    
    def list_providers(self) -> list[Provider]:
        pass
```

## Tool Registry

```python
# Nuevo componente para tools
class ToolRegistry:
    """Registry of available tools for step execution."""
    
    def register(self, name: str, func: Callable, schema: dict):
        pass
    
    async def execute(self, name: str, args: dict, context: ExecutionContext) -> Any:
        pass
```

---

# ORDEN DE IMPLEMENTACIÓN

## Sprint 1: Planner (5 días)

1. **Día 1-2**: `cosmos/planner/types.py`
   - Definir `Step`, `Plan`, `PlanStatus`
   - Tests unitarios

2. **Día 3-4**: `cosmos/planner/llm_planner.py`
   - Usar SmartRouter para obtener LLM provider
   - Prompt engineering para decomposition
   - Parsear respuesta a Plan

3. **Día 5**: `cosmos/planner/cosmos_planner.py`
   - Generar Cosmos DSL desde plan
   - Integrar con DAG existente

**Tests**: Mínimo 15 tests cubriendo:
- Plan creation
- Step dependencies
- DAG validation
- LLM parsing

---

## Sprint 2: Scheduler (3 días)

1. **Día 1**: `cosmos/scheduler/types.py` + `task_queue.py`
   - Priority queue con dependencia awareness
   - Algoritmo de topological scheduling

2. **Día 2**: `cosmos/scheduler/dag_scheduler.py`
   - Ready step detection
   - Parallel execution con semaphore
   - Retry logic

3. **Día 3**: `cosmos/scheduler/human_in_loop.py`
   - Approval hooks
   - Timeout handling

**Tests**: Mínimo 10 tests cubriendo:
- DAG scheduling
- Dependency resolution
- Parallel execution
- Retry logic

---

## Sprint 3: Executor (5 días)

1. **Día 1**: `cosmos/executor/types.py` + `context_manager.py`
   - `StepResult`, `ExecutionContext`
   - Shared state management
   - Audit logging

2. **Día 2-3**: `cosmos/executor/step_executor.py`
   - Provider integration
   - Tool execution
   - Result caching

3. **Día 4**: `cosmos/executor/tool_registry.py`
   - Tool registration
   - Tool execution
   - Error handling

4. **Día 5**: `cosmos/executor/error_handler.py`
   - Error classification
   - Recovery strategies

**Tests**: Mínimo 15 tests cubriendo:
- Step execution
- Tool execution
- Error handling
- Context propagation

---

## Sprint 4: Integración (3 días)

1. **Día 1**: `cosmos/engine.py` ( orchestration completo)
   - Planner → Scheduler → Executor
   - Event emission
   - Result aggregation

2. **Día 2**: Integration tests
   - End-to-end workflows
   - Complex DAG execution
   - Error scenarios

3. **Día 3**: Documentation + Examples
   - Usage examples
   - API documentation
   - Migration guide

---

# EJEMPLO DE EJECUCIÓN

## Input

```
Task: "Research the top 5 coffee providers in Mexico, analyze their prices, 
       and create a summary report comparing them."
```

## Plan Generado

```python
Plan(
    id="plan_abc123",
    task="Research coffee providers...",
    steps=[
        Step(id="s1", name="Research", provider=GROK, 
              prompt="Research coffee providers...", dependencies=[]),
        Step(id="s2", name="Analyze", provider=CLAUDE,
              prompt="Analyze prices...", dependencies=["s1"]),
        Step(id="s3", name="Summarize", provider=GPT4,
              prompt="Create summary...", dependencies=["s2"]),
    ]
)
```

## DAG

```
s1 (Research) ──▶ s2 (Analyze) ──▶ s3 (Summarize)
```

## Execution

```
[00:00.0] Scheduler: s1 is ready (no dependencies)
[00:00.1] Executor: Starting s1 (Research)
[00:02.5] Executor: s1 completed (2.5s, $0.001)
[00:02.5] Scheduler: s2 is ready (s1 done)
[00:02.6] Executor: Starting s2 (Analyze)
[00:05.1] Executor: s2 completed (2.5s, $0.002)
[00:05.1] Scheduler: s3 is ready (s2 done)
[00:05.2] Executor: Starting s3 (Summarize)
[00:07.3] Executor: s3 completed (2.1s, $0.001)
[00:07.3] Plan completed: 7.3s total, $0.004 total
```

---

# RIESGOS Y MITIGACIONES

| Riesgo | Severidad | Probabilidad | Mitigación |
|--------|-----------|-------------|------------|
| LLM Planner genera planes inválidos | HIGH | MEDIUM | Validación de plan + fallback a simple |
| Ciclos en dependencias | MEDIUM | LOW | DAG cycle detection ya existe |
| Timeout en steps largos | MEDIUM | MEDIUM | Configurable timeouts + retry |
| Cost overruns | HIGH | MEDIUM | Cost limits + budget checks |
| Provider unavailable | MEDIUM | MEDIUM | Multi-provider fallback |
| Memory leaks en ejecución larga | LOW | LOW | Context cleanup + limits |

---

# MCP/A2A INTEROPERABILIDAD (2026)

Para 2026, el sistema debe ser interoperable:

```python
# MCP (Model Context Protocol) integration
class MCPAdapter:
    """Adapter for MCP-compatible tools."""
    async def execute_mcp_tool(self, tool: MCPTool, context: ExecutionContext):
        pass

# A2A (Agent-to-Agent) integration  
class A2AAdapter:
    """Adapter for A2A messaging."""
    async def send_message(self, agent_id: str, message: A2AMessage):
        pass
    
    async def receive_message(self) -> A2AMessage:
        pass
```

**Nota:** Implementar stubs ahora, funcionalidad completa en v0.7.

---

# CRITERIOS DE ÉXITO

## Al finalizar Sprint 1 (Planner)

- [ ] `python -c "from cosmos.planner import Planner; print('OK')"` funciona
- [ ] Planner genera un Plan válido para tarea simple
- [ ] 15+ tests pasando

## Al finalizar Sprint 2 (Scheduler)

- [ ] 3 tasks en paralelo con dependencias correctas
- [ ] Retry funciona cuando un step falla
- [ ] 10+ tests pasando

## Al finalizar Sprint 3 (Executor)

- [ ] Step ejecuta correctamente con provider
- [ ] Tools se ejecutan
- [ ] 15+ tests pasando

## Al finalizar Sprint 4 (Integración)

- [ ] End-to-end: task → plan → execute → result
- [ ] 132+ tests pasando (todos los existentes)
- [ ] Ejemplo ejecutable en examples/

---

# NO HACER (Constraints)

- ❌ No modificar Cosmos Parser existente
- ❌ No modificar DAG existente
- ❌ No modificar SmartRouter existente
- ❌ No agregar features fuera del core
- ❌ No romper compatibilidad hacia atrás

---

# ARCHIVOS A MODIFICAR

## Existentes

| Archivo | Cambio |
|---------|--------|
| `cosmos/__init__.py` | Agregar exports del planner/scheduler/executor |
| `solvens/__init__.py` | Agregar exports |
| `tests/test_cosmos.py` | Agregar tests de integración |

## Nuevos

| Archivo | Descripción |
|---------|-------------|
| `cosmos/planner/types.py` | Tipos del planner |
| `cosmos/planner/llm_planner.py` | LLM planner |
| `cosmos/scheduler/types.py` | Tipos del scheduler |
| `cosmos/scheduler/dag_scheduler.py` | DAG scheduler |
| `cosmos/executor/types.py` | Tipos del executor |
| `cosmos/executor/step_executor.py` | Step executor |
| `cosmos/engine.py` | Orquestación completa |

---

# PRÓXIMO PASO

**Esperar aprobación de Luis antes de ejecutar.**

Una vez aprobado:
1. Crear archivos incrementalmente
2. Tests después de cada componente
3. Integration test al final
4. Actualizar PROJECT_STATUS_REPORT.md
