"""Cosmos AST (Abstract Syntax Tree) module.

Defines the fundamental AST structures for the Cosmos language.
Each node contains structural identity, type, properties, relations, and canonical hash.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CosmosNodeType(Enum):
    """Node types in Cosmos AST."""
    
    # Core types
    PROGRAM = "program"
    STATEMENT = "statement"
    EXPRESSION = "expression"
    
    # Entity types
    ENTITY = "entity"
    TASK = "task"
    AGENT = "agent"
    TOOL = "tool"
    PROVIDER = "provider"
    
    # Operation types
    ACTION = "action"
    QUERY = "query"
    TRANSFORM = "transform"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    
    # Control flow
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    
    # Data types
    VALUE = "value"
    LIST = "list"
    DICT = "dict"
    REFERENCE = "reference"
    
    # Metadata
    COMMENT = "comment"
    METADATA = "metadata"
    ANNOTATION = "annotation"


@dataclass
class CosmosNode:
    """Base node for Cosmos AST.
    
    Every node has:
    - Structural ID (UUID)
    - Node type
    - Properties (key-value)
    - Relations (parent, children)
    - Metadata
    - Canonical hash
    """
    
    node_type: CosmosNodeType
    properties: dict[str, Any] = field(default_factory=dict)
    relations: dict[str, list[CosmosNode]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    parent: CosmosNode | None = None
    
    # Generated fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    canonical_hash: str = ""
    
    def __post_init__(self):
        """Generate canonical hash after initialization."""
        self._update_canonical_hash()
    
    def _update_canonical_hash(self) -> None:
        """Update the canonical hash of this node."""
        content = self._get_hashable_content()
        self.canonical_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_hashable_content(self) -> str:
        """Get hashable content for canonical hashing."""
        parts = [
            self.node_type.value,
            str(sorted(self.properties.items())),
        ]
        return "|".join(parts)
    
    def add_child(self, relation: str, child: CosmosNode) -> None:
        """Add a child node with a relation type."""
        child.parent = self
        if relation not in self.relations:
            self.relations[relation] = []
        self.relations[relation].append(child)
        self._update_canonical_hash()
    
    def get_children(self, relation: str | None = None) -> list[CosmosNode]:
        """Get child nodes, optionally filtered by relation."""
        if relation:
            return self.relations.get(relation, [])
        return [child for children in self.relations.values() for child in children]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "id": self.id,
            "type": self.node_type.value,
            "properties": self.properties,
            "relations": {
                rel: [child.to_dict() for child in children]
                for rel, children in self.relations.items()
            },
            "metadata": self.metadata,
            "canonical_hash": self.canonical_hash,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CosmosNode:
        """Create node from dictionary representation."""
        node = cls(
            node_type=CosmosNodeType(data["type"]),
            properties=data.get("properties", {}),
            metadata=data.get("metadata", {}),
            id=data.get("id", str(uuid.uuid4())),
        )
        if "created_at" in data:
            node.created_at = datetime.fromisoformat(data["created_at"])
        return node
    
    def copy(self) -> CosmosNode:
        """Create a deep copy of this node."""
        new_node = CosmosNode(
            node_type=self.node_type,
            properties=self.properties.copy(),
            metadata=self.metadata.copy(),
        )
        # Copy children recursively
        for relation, children in self.relations.items():
            for child in children:
                new_node.add_child(relation, child.copy())
        return new_node


@dataclass
class CosmosEntity(CosmosNode):
    """Represents an entity in the Cosmos universe.
    
    Entities are the fundamental building blocks that can be:
    - Tasks
    - Agents
    - Tools
    - Providers
    - Resources
    """
    
    def __init__(self, name: str, entity_type: str, **kwargs):
        super().__init__(
            node_type=CosmosNodeType.ENTITY,
            properties={"name": name, "entity_type": entity_type},
            **kwargs
        )


@dataclass
class CosmosRelation:
    """Represents a typed relation between entities."""
    
    source_id: str
    target_id: str
    relation_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type,
            "properties": self.properties,
            "metadata": self.metadata,
        }


class CosmosAST:
    """Abstract Syntax Tree for Cosmos programs.
    
    The AST is the primary representation of parsed Cosmos code.
    It maintains structural identity and can be canonicalized.
    """
    
    def __init__(self):
        self.root: CosmosNode = CosmosNode(node_type=CosmosNodeType.PROGRAM)
        self.nodes: dict[str, CosmosNode] = {}
        self.relations: list[CosmosRelation] = []
        self._index_node(self.root)
    
    def _index_node(self, node: CosmosNode) -> None:
        """Index a node by its ID."""
        self.nodes[node.id] = node
    
    def add_node(self, node: CosmosNode, parent: CosmosNode | None = None, relation: str = "child") -> None:
        """Add a node to the AST."""
        self._index_node(node)
        if parent:
            parent.add_child(relation, node)
        else:
            self.root.add_child(relation, node)
    
    def find_node(self, node_id: str) -> CosmosNode | None:
        """Find a node by ID."""
        return self.nodes.get(node_id)
    
    def find_nodes(self, predicate: callable) -> list[CosmosNode]:
        """Find all nodes matching a predicate."""
        return [n for n in self.nodes.values() if predicate(n)]
    
    def get_all_nodes(self) -> list[CosmosNode]:
        """Get all nodes in the AST."""
        return list(self.nodes.values())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert AST to dictionary representation."""
        return {
            "root": self.root.to_dict(),
            "nodes_count": len(self.nodes),
            "relations_count": len(self.relations),
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "relations": [r.to_dict() for r in self.relations],
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CosmosAST:
        """Create AST from dictionary representation."""
        ast = cls()
        # Rebuild AST from data
        # (Simplified - full implementation would recursively rebuild)
        return ast
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate the AST structure.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check root is program
        if self.root.node_type != CosmosNodeType.PROGRAM:
            errors.append("Root node must be PROGRAM type")
        
        # Check all nodes have valid types
        for node_id, node in self.nodes.items():
            if not isinstance(node.node_type, CosmosNodeType):
                errors.append(f"Node {node_id} has invalid type")
        
        # Check circular references
        if self._has_circular_references():
            errors.append("AST contains circular references")
        
        return len(errors) == 0, errors
    
    def _has_circular_references(self) -> bool:
        """Check if AST has circular references."""
        visited = set()
        path = set()
        
        def visit(node: CosmosNode) -> bool:
            if node.id in path:
                return True
            if node.id in visited:
                return False
            
            path.add(node.id)
            for child in node.get_children():
                if visit(child):
                    return True
            path.remove(node.id)
            visited.add(node.id)
            return False
        
        return visit(self.root)
