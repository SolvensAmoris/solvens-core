"""
SOLVENS Cosmos

AI Agent Orchestration Platform.
Provider-agnostic, cost-safe, RBAC-protected.
"""

__version__ = "1.1.0"

from cosmos.parser.parser import Parser
from cosmos.parser.lexer import Lexer
from cosmos.ast import ASTNode, Program, TaskDecl, AgentDecl, ProviderDecl
from cosmos.dag import DAG, CycleError
from cosmos.engine import Engine, EngineConfig, run_task

# Planner
from cosmos.planner import (
    Plan,
    PlanNode,
    PlanStatus,
    StepStatus,
    LLMPlanner,
)

# Scheduler
from cosmos.scheduler import DAGScheduler

# Executor
from cosmos.executor import StepExecutor, StepResult, ToolRegistry

__all__ = [
    # Version
    "__version__",
    # Parser
    "Parser",
    "Lexer",
    "ASTNode",
    "Program",
    "TaskDecl",
    "AgentDecl",
    "ProviderDecl",
    # DAG
    "DAG",
    "CycleError",
    # Engine
    "Engine",
    "EngineConfig",
    "run_task",
    # Planner
    "Plan",
    "PlanNode",
    "PlanStatus",
    "StepStatus",
    "LLMPlanner",
    # Scheduler
    "DAGScheduler",
    # Executor
    "StepExecutor",
    "StepResult",
    "ToolRegistry",
]
