"""Cosmos DAG (Directed Acyclic Graph) module.

The DAG is the canonical representation of computational flow in Cosmos.
Each node represents an operation or entity, and edges represent dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections import deque


class DAGEdgeType(Enum):
    """Types of edges in the DAG."""
    
    DEPENDENCY = "dependency"      # Execution dependency
    DATA_FLOW = "data_flow"        # Data passing
    CONTROL_FLOW = "control_flow"  # Control dependencies
    REFERENCE = "reference"         # Reference to entity


class DAGNodeStatus(Enum):
    """Status of a DAG node during execution."""
    
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGEdge:
    """Represents an edge in the DAG.
    
    Edges represent dependencies between nodes.
    """
    
    source_id: str
    target_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    edge_type: DAGEdgeType = DAGEdgeType.DEPENDENCY
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source_id,
            "target": self.target_id,
            "type": self.edge_type.value,
            "properties": self.properties,
            "metadata": self.metadata,
        }


@dataclass
class DAGNode:
    """Represents a node in the DAG.
    
    Each node contains:
    - Operation or entity definition
    - Dependencies (incoming edges)
    - Dependents (outgoing edges)
    - Execution metadata
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    node_type: str = "operation"
    operation: str = ""           # What to execute
    provider: str | None = None   # Recommended provider
    agent: str | None = None      # Recommended agent
    tool: str | None = None       # Recommended tool
    
    # Input/Output
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    dependencies: list[str] = field(default_factory=list)  # Node IDs this depends on
    dependents: list[str] = field(default_factory=list)   # Node IDs that depend on this
    
    # Execution metadata
    priority: int = 50            # 0-100, higher = more priority
    estimated_cost: float = 0.0   # Estimated computational cost
    estimated_duration: float = 0.0  # Estimated time in seconds
    status: DAGNodeStatus = DAGNodeStatus.PENDING
    
    # Metadata
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "operation": self.operation,
            "provider": self.provider,
            "agent": self.agent,
            "tool": self.tool,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "priority": self.priority,
            "estimated_cost": self.estimated_cost,
            "estimated_duration": self.estimated_duration,
            "status": self.status.value,
            "properties": self.properties,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DAGNode:
        """Create DAGNode from dictionary."""
        node = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            node_type=data.get("type", "operation"),
            operation=data.get("operation", ""),
            provider=data.get("provider"),
            agent=data.get("agent"),
            tool=data.get("tool"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            dependencies=data.get("dependencies", []),
            dependents=data.get("dependents", []),
            priority=data.get("priority", 50),
            estimated_cost=data.get("estimated_cost", 0.0),
            estimated_duration=data.get("estimated_duration", 0.0),
            status=DAGNodeStatus(data.get("status", "pending")),
            properties=data.get("properties", {}),
            metadata=data.get("metadata", {}),
        )
        if data.get("created_at"):
            node.created_at = datetime.fromisoformat(data["created_at"])
        return node


class CosmosDAG:
    """Directed Acyclic Graph for Cosmos execution.
    
    The DAG represents the computational flow as a directed graph
    with no cycles. It can be analyzed for:
    - Parallel execution opportunities
    - Critical path
    - Resource optimization
    - Dependency resolution
    """
    
    def __init__(self):
        self.id: str = str(uuid.uuid4())
        self.nodes: dict[str, DAGNode] = {}
        self.edges: dict[str, DAGEdge] = {}
        self.root_nodes: list[str] = []   # Nodes with no dependencies
        self.leaf_nodes: list[str] = []    # Nodes with no dependents
        self.created_at: datetime = datetime.utcnow()
        self.metadata: dict[str, Any] = {}
    
    def add_node(self, node: DAGNode) -> None:
        """Add a node to the DAG."""
        self.nodes[node.id] = node
        self._update_roots_and_leaves()
    
    def add_edge(self, edge: DAGEdge) -> None:
        """Add an edge to the DAG.
        
        Args:
            edge: The edge to add (source must exist)
            
        Raises:
            ValueError: If source or target node doesn't exist
        """
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} not found")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} not found")
        
        self.edges[edge.id] = edge
        
        # Update node dependencies
        source = self.nodes[edge.source_id]
        target = self.nodes[edge.target_id]
        
        if edge.target_id not in source.dependents:
            source.dependents.append(edge.target_id)
        if edge.source_id not in target.dependencies:
            target.dependencies.append(edge.source_id)
        
        self._update_roots_and_leaves()
    
    def get_node(self, node_id: str) -> DAGNode | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_ready_nodes(self) -> list[DAGNode]:
        """Get all nodes that are ready to execute.
        
        A node is ready if all its dependencies have completed.
        """
        ready = []
        for node in self.nodes.values():
            if node.status != DAGNodeStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            all_deps_done = all(
                self.nodes[dep_id].status == DAGNodeStatus.COMPLETED
                for dep_id in node.dependencies
                if dep_id in self.nodes
            )
            
            if all_deps_done:
                ready.append(node)
        
        return ready
    
    def get_parallelizable_nodes(self) -> list[list[DAGNode]]:
        """Get nodes that can be executed in parallel.
        
        Returns a list of layers, where each layer contains
        nodes that can be executed concurrently.
        """
        layers: list[list[DAGNode]] = []
        processed = set()
        
        while len(processed) < len(self.nodes):
            # Find ready nodes that haven't been processed
            ready = [
                n for n in self.get_ready_nodes()
                if n.id not in processed
            ]
            
            if not ready:
                break
            
            layers.append(ready)
            processed.update(n.id for n in ready)
        
        return layers
    
    def topological_sort(self) -> list[DAGNode]:
        """Get nodes in topological order.
        
        Returns nodes sorted such that dependencies come before dependents.
        """
        # Calculate in-degrees
        in_degree = {node_id: len(node.dependencies) for node_id, node in self.nodes.items()}
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            node = self.nodes[node_id]
            result.append(node)
            
            for dependent_id in node.dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        if len(result) != len(self.nodes):
            raise ValueError("DAG contains a cycle")
        
        return result
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate the DAG structure.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check for cycles
        if self._has_cycle():
            errors.append("DAG contains a cycle")
        
        # Check for missing dependencies
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    errors.append(f"Node {node_id} depends on missing node {dep_id}")
        
        return len(errors) == 0, errors
    
    def _has_cycle(self) -> bool:
        """Check if DAG contains a cycle using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for dependent_id in self.nodes[node_id].dependents:
                if dependent_id not in visited:
                    if dfs(dependent_id):
                        return True
                elif dependent_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    def _update_roots_and_leaves(self) -> None:
        """Update root and leaf node lists."""
        self.root_nodes = [
            node_id for node_id, node in self.nodes.items()
            if not node.dependencies
        ]
        self.leaf_nodes = [
            node_id for node_id, node in self.nodes.items()
            if not node.dependents
        ]
    
    def get_statistics(self) -> dict[str, Any]:
        """Get DAG statistics."""
        completed = sum(1 for n in self.nodes.values() if n.status == DAGNodeStatus.COMPLETED)
        running = sum(1 for n in self.nodes.values() if n.status == DAGNodeStatus.RUNNING)
        failed = sum(1 for n in self.nodes.values() if n.status == DAGNodeStatus.FAILED)
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "root_nodes": len(self.root_nodes),
            "leaf_nodes": len(self.leaf_nodes),
            "parallel_layers": len(self.get_parallelizable_nodes()),
            "status": {
                "completed": completed,
                "running": running,
                "pending": len(self.nodes) - completed - running - failed,
                "failed": failed,
            },
            "estimated_cost": sum(n.estimated_cost for n in self.nodes.values()),
            "estimated_duration": self._estimate_duration(),
        }
    
    def _estimate_duration(self) -> float:
        """Estimate total duration considering parallelism."""
        layers = self.get_parallelizable_nodes()
        total = 0.0
        for layer in layers:
            max_duration = max((n.estimated_duration for n in layer), default=0.0)
            total += max_duration
        return total
    
    def to_dict(self) -> dict[str, Any]:
        """Convert DAG to dictionary representation."""
        return {
            "id": self.id,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": {edge_id: edge.to_dict() for edge_id, edge in self.edges.items()},
            "root_nodes": self.root_nodes,
            "leaf_nodes": self.leaf_nodes,
            "metadata": self.metadata,
            "statistics": self.get_statistics(),
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CosmosDAG:
        """Create DAG from dictionary representation."""
        dag = cls()
        dag.id = data.get("id", str(uuid.uuid4()))
        dag.metadata = data.get("metadata", {})
        
        # Rebuild nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node = DAGNode.from_dict(node_data)
            dag.nodes[node_id] = node
        
        # Rebuild edges
        for edge_id, edge_data in data.get("edges", {}).items():
            edge = DAGEdge(
                id=edge_id,
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                edge_type=DAGEdgeType(edge_data.get("type", "dependency")),
                properties=edge_data.get("properties", {}),
            )
            dag.edges[edge_id] = edge
        
        dag.root_nodes = data.get("root_nodes", [])
        dag.leaf_nodes = data.get("leaf_nodes", [])
        
        return dag
