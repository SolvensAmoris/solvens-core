# Cosmos Architecture

**Version:** 0.1.0  
**Part of:** SOLVENS CORE

---

## Overview

Cosmos is a **computational representation language** that serves as the universal intermediate representation (IR) for SOLVENS CORE. It transforms natural language input into structured, executable task graphs.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Input                                  │
│                    (Natural Language / DSL / JSON)                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Cosmos Parser                               │
│                      (Lexer → Token → AST)                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Cosmos AST                                     │
│         (Abstract Syntax Tree with Structural Identity)                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Cosmos Canonicalizer                             │
│              (Deduplication, Ordering, Hashing)                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Cosmos DAG                                    │
│              (Directed Acyclic Graph of Operations)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Cosmos Planner                                  │
│          (Task Decomposition, Parallelization, Optimization)          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Cosmos Runtime                                   │
│                (Execution Coordination, Synchronization)               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SOLVENS CORE                                      │
│              (Agent Orchestrator + Capability Router)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Providers                                     │
│                  (OpenAI, Anthropic, Ollama, etc.)                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. AST (Abstract Syntax Tree)

The foundational representation of Cosmos programs.

```python
CosmosAST
├── root: CosmosNode (PROGRAM)
├── nodes: dict[str, CosmosNode]
├── relations: list[CosmosRelation]
```

**Node Structure:**
```python
CosmosNode
├── id: str (UUID)
├── node_type: CosmosNodeType
├── properties: dict[str, Any]
├── relations: dict[str, list[CosmosNode]]
├── metadata: dict[str, Any]
├── parent: CosmosNode | None
├── created_at: datetime
└── canonical_hash: str
```

### 2. DAG (Directed Acyclic Graph)

The canonical execution representation.

```python
CosmosDAG
├── id: str
├── nodes: dict[str, DAGNode]
├── edges: dict[str, DAGEdge]
├── root_nodes: list[str]
└── leaf_nodes: list[str]
```

**Node in DAG:**
```python
DAGNode
├── id: str
├── name: str
├── node_type: str
├── operation: str
├── provider: str | None
├── agent: str | None
├── dependencies: list[str]
├── dependents: list[str]
├── priority: int (0-100)
├── estimated_cost: float
├── estimated_duration: float
└── status: DAGNodeStatus
```

### 3. Parser

Transforms input into AST.

**Supported Formats:**
- **DSL**: Custom Cosmos syntax
- **JSON**: Structured JSON representation
- **Natural Language**: (experimental)

**Example DSL:**
```cosmos
task: create_report
    provider = anthropic
    priority = 80
    
    sequence: data_collection
        task: fetch_data
            tool = database_query
        task: process_data
            tool = python
    
    parallel: analysis
        task: calculate_metrics
        task: generate_charts
```

**Example JSON:**
```json
{
    "root": {
        "type": "program",
        "properties": {"name": "create_report"},
        "relations": {
            "tasks": [
                {
                    "type": "task",
                    "properties": {
                        "name": "fetch_data",
                        "provider": "anthropic"
                    }
                }
            ]
        }
    }
}
```

### 4. Canonicalizer

Ensures deterministic representation.

**Functions:**
- Sort children by type and name
- Remove duplicate nodes
- Compute canonical hashes
- Compare ASTs (diff)
- Merge ASTs

### 5. Planner

Transforms DAG into executable plan.

**Outputs:**
```python
ExecutionPlan
├── dag_id: str
├── phases: list[ExecutionPhase]
├── total_cost: float
└── total_duration: float

ExecutionPhase
├── phase_id: str
├── order: int
├── nodes: list[str]
├── parallel: bool
├── estimated_duration: float
└── status: PhaseStatus
```

### 6. Runtime

Coordinates execution.

**Responsibilities:**
- Interpret DAG
- Wait for dependencies
- Synchronize results
- Handle errors
- Reconstruct output

## Data Flow

### Input → Execution

1. **Parse**: Transform input to AST
2. **Canonicalize**: Normalize structure
3. **Build DAG**: Convert to dependency graph
4. **Plan**: Generate execution phases
5. **Execute**: Coordinate through Runtime
6. **Route**: Delegate to Capability Router
7. **Execute**: Run via Providers
8. **Return**: Reconstruct and return results

### Example: Natural Language Input

```
Input: "Create a report analyzing our Q4 sales data"
```

**Step 1: Parse**
```python
# CosmosParser parses natural language
AST: {
    nodes: [
        CosmosNode(type=TASK, properties={name: "q4_sales_report"})
    ]
}
```

**Step 2: Canonicalize**
```python
canonical_hash: "abc123..."
```

**Step 3: Build DAG**
```python
DAG: {
    nodes: {
        "task_1": DAGNode(name="fetch_sales", provider="database"),
        "task_2": DAGNode(name="analyze_data", provider="anthropic"),
        "task_3": DAGNode(name="generate_report", provider="grok")
    },
    edges: [
        ("task_1", "task_2"),  # depends on
        ("task_2", "task_3")   # depends on
    ]
}
```

**Step 4: Plan**
```python
ExecutionPlan: {
    phases: [
        Phase(order=0, nodes=["task_1"], parallel=False),
        Phase(order=1, nodes=["task_2"], parallel=False),
        Phase(order=2, nodes=["task_3"], parallel=False)
    ]
}
```

**Step 5: Execute**
- Runtime coordinates phase execution
- Tasks routed to appropriate providers
- Results collected and synchronized

## Key Design Decisions

### 1. Separation of Concerns

```
Cosmos: Representation and Planning
SOLVENS CORE: Orchestration and Execution
Providers: Task Execution
```

### 2. Provider Independence

Providers never see raw user input. They receive:
```python
{
    "task": "analyze_data",
    "inputs": {...},
    "context": {...},
    "expected_output": {...}
}
```

### 3. Structural Identity

Every node has a canonical hash enabling:
- Deduplication
- Caching
- Comparison
- Version control

### 4. Parallelization Detection

The planner automatically identifies:
- Nodes with no dependencies (can run in parallel)
- Pipeline stages (must run sequentially)
- Optimal execution order

## API Integration

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cosmos/parse` | POST | Parse input to AST |
| `/api/cosmos/ast` | GET | Get AST details |
| `/api/cosmos/dag` | POST | Build DAG from AST |
| `/api/cosmos/plan` | POST | Generate execution plan |
| `/api/cosmos/execute` | POST | Execute plan |
| `/api/cosmos/visualize` | GET | Get DAG visualization |

### CLI Commands

```bash
solvens cosmos parse "Create a report"
solvens cosmos dag --ast <ast_id>
solvens cosmos plan --dag <dag_id>
solvens cosmos execute --plan <plan_id>
solvens cosmos visualize --dag <dag_id>
```

## Future Enhancements

- **Natural Language Parser**: ML-based intent recognition
- **Optimization**: Subgraph detection and fusion
- **Caching**: Result caching based on canonical hash
- **Visualization**: Interactive DAG viewer
- **Versioning**: AST versioning and history
- **Collaboration**: Multi-user AST editing
