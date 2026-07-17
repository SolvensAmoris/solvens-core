"""SOLVENS CORE - Cosmos Language Integration.

Cosmos is a computational representation language that serves as the universal
intermediate representation (IR) for task planning and execution in SOLVENS CORE.

Architecture:
    User Input → Cosmos Parser → AST → Canonicalizer → DAG → Planner → Executor
                                                                            ↓
                                                            Capability Router → Providers

Cosmos is NOT:
- A provider of AI
- A model
- A plugin

Cosmos IS:
- A representation layer (AST, DAG)
- A planning engine
- An optimization layer
- A universal IR between user intent and provider execution
"""

from __future__ import annotations

__version__ = "0.1.0"

from solvens.cosmos.ast import (
    CosmosNode,
    CosmosNodeType,
    CosmosAST,
    CosmosEntity,
    CosmosRelation,
)
from solvens.cosmos.dag import CosmosDAG, DAGNode, DAGEdge
from solvens.cosmos.parser import CosmosParser
from solvens.cosmos.canonicalizer import CosmosCanonicalizer
from solvens.cosmos.planner import CosmosPlanner
from solvens.cosmos.runtime import CosmosRuntime
from solvens.cosmos.executor import CosmosExecutor

__all__ = [
    # Version
    "__version__",
    # AST
    "CosmosNode",
    "CosmosNodeType", 
    "CosmosAST",
    "CosmosEntity",
    "CosmosRelation",
    # DAG
    "CosmosDAG",
    "DAGNode",
    "DAGEdge",
    # Core components
    "CosmosParser",
    "CosmosCanonicalizer",
    "CosmosPlanner",
    "CosmosRuntime",
    "CosmosExecutor",
]
