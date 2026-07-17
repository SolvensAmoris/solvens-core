"""
SOLVENS Cosmos

AI Agent Orchestration Platform.
Provider-agnostic, cost-safe, RBAC-protected.
"""

__version__ = "1.0.0"

from cosmos.parser.parser import Parser
from cosmos.parser.lexer import Lexer
from cosmos.ast import ASTNode, Program, TaskDecl, AgentDecl, ProviderDecl

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
