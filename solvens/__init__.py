"""
SOLVENS CORE

AI Agent Orchestration Platform.

Usage:
    from solvens import CosmosCompilerAgent, Executor, CostEstimator
    
    agent = CosmosCompilerAgent()
    result = agent.compile("workflow.cosmos")
"""

__version__ = "1.0.0"

# Core components
from cosmos.parser.parser import Parser
from cosmos.parser.lexer import Lexer
from cosmos.ast import ASTNode, Program, TaskDecl, AgentDecl, ProviderDecl

# Providers
try:
    from cosmos.providers import llm, BaseProvider, ProviderType, Message
except ImportError:
    pass

# Runtime
try:
    from cosmos.runtime.cost_safety import (
        cost_estimator,
        budget_manager,
        CostEstimator,
        BudgetManager,
        CircuitBreaker,
    )
except ImportError:
    pass

# Security
try:
    from cosmos.security.rbac import rbac, Role, Permission
except ImportError:
    pass

__all__ = [
    "__version__",
    "Parser",
    "Lexer",
    "ASTNode",
    "Program",
    "TaskDecl",
    "AgentDecl",
    "ProviderDecl",
]
