"""
COSMOS AST Nodes

Defines the Abstract Syntax Tree nodes for COSMOS language.
Includes visitor pattern for traversing the AST.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar, Generic

# Type variable for visitor return type
T = TypeVar('T')

@dataclass
class ASTNode(ABC):
    """Base class for all AST nodes."""

    @abstractmethod
    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        """Accept a visitor."""
        pass

@dataclass
class Program(ASTNode):
    """Root node representing a complete program."""
    statements: list[ASTNode]

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_program(self)

@dataclass
class TaskDecl(ASTNode):
    """Task declaration node."""
    name: str
    properties: list['Property']

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_task(self)

@dataclass
class AgentDecl(ASTNode):
    """Agent declaration node."""
    name: str
    properties: list['Property']

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_agent(self)

@dataclass
class ProviderDecl(ASTNode):
    """Provider declaration node."""
    name: str
    properties: list['Property']

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_provider(self)

@dataclass
class DagDecl(ASTNode):
    """DAG declaration node."""
    name: str
    edges: list[tuple[str, str]] # List of (from, to) tuples

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_dag(self)

@dataclass
class Property(ASTNode):
    """Property assignment node."""
    name: str
    value: Any # Can be str, int, list, bool

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_property(self)

@dataclass
class SeedDecl(ASTNode):
    """
    Nodo SEMILLA OFICIAL — StarkCore Channel 7.
    seed_bytes -> canonical_encode -> [SUN, NODE, ROOT, FLOW,...]
    REGLAS: tokens = ORDERED, name = UNORDERED
    """
    name: str
    tokens: list[str]
    bit_length: int = 128

    def accept(self, visitor: 'NodeVisitor[T]') -> T:
        return visitor.visit_seed(self)

class NodeVisitor(ABC, Generic[T]):
    """
    Visitor pattern interface for AST traversal.
    """

    @abstractmethod
    def visit_program(self, node: Program) -> T:
        pass

    @abstractmethod
    def visit_task(self, node: TaskDecl) -> T:
        pass

    @abstractmethod
    def visit_agent(self, node: AgentDecl) -> T:
        pass

    @abstractmethod
    def visit_provider(self, node: ProviderDecl) -> T:
        pass

    @abstractmethod
    def visit_dag(self, node: DagDecl) -> T:
        pass

    @abstractmethod
    def visit_property(self, node: Property) -> T:
        pass

    @abstractmethod
    def visit_seed(self, node: SeedDecl) -> T:
        pass

class ASTHasher:
    """
    Generates a unique hash for an AST node.
    Used for canonicalization and caching.
    """

    @staticmethod
    def hash_node(node: ASTNode) -> str:
        """Generate a deterministic hash for a node."""
        return ASTHasher()._visit(node)

    def _visit(self, node: ASTNode) -> str:
        """Visit a node and return its hash."""
        if isinstance(node, Program):
            stmts = [self._visit(s) for s in node.statements]
            return f"Program({','.join(stmts)})"
        elif isinstance(node, TaskDecl):
            props = [self._visit(p) for p in node.properties]
            return f"Task({node.name}[{','.join(props)}])"
        elif isinstance(node, AgentDecl):
            props = [self._visit(p) for p in node.properties]
            return f"Agent({node.name}[{','.join(props)}])"
        elif isinstance(node, ProviderDecl):
            props = [self._visit(p) for p in node.properties]
            return f"Provider({node.name}[{','.join(props)}])"
        elif isinstance(node, DagDecl):
            edges = [f"{f}->{t}" for f, t in node.edges]
            return f"DAG({node.name}[{','.join(edges)}])"
        elif isinstance(node, Property):
            val = str(node.value)
            return f"Prop({node.name}={val})"
        elif isinstance(node, SeedDecl):
            token_list = ",".join(node.tokens)
            return f"Seed({node.name}|{node.bit_length}|[{token_list}])"
        else:
            return "Unknown()"