"""
Solvens Compatibility Layer
===========================

Adapters for compatibility with other frameworks.

Author: Luis Alberto Burciaga Miker
Version: 0.5.0
"""

from .langgraph_adapter import (
    LangGraphAdapter,
    CosmosDAG,
    CosmosNode,
    CosmosEdge,
    CosmosNodeType,
    create_migration_guide,
)

__all__ = [
    "LangGraphAdapter",
    "CosmosDAG",
    "CosmosNode",
    "CosmosEdge",
    "CosmosNodeType",
    "create_migration_guide",
]

__version__ = "0.5.0"
