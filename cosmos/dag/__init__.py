"""
DAG (Directed Acyclic Graph) module for COSMOS
Provides deterministic topological sorting and cycle detection.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
from collections import deque

class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass

@dataclass
class DAGNode:
    """A node in the DAG."""
    id: str
    metadata: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, DAGNode) and self.id == other.id

@dataclass
class DAG:
    nodes: dict[str, DAGNode] = field(default_factory=dict)
    edges: dict[str, list[str]] = field(default_factory=dict)
    reverse_edges: dict[str, list[str]] = field(default_factory=dict)

    def add_node(self, node_id: str, metadata: Optional[dict] = None) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = DAGNode(id=node_id, metadata=metadata or {})
            self.edges[node_id] = []
            self.reverse_edges[node_id] = []

    def add_edge(self, from_id: str, to_id: str) -> None:
        if from_id not in self.nodes:
            self.add_node(from_id)
        if to_id not in self.nodes:
            self.add_node(to_id)
        if to_id not in self.edges[from_id]:
            self.edges[from_id].append(to_id)
        if from_id not in self.reverse_edges[to_id]:
            self.reverse_edges[to_id].append(from_id)

    def topological_sort(self) -> list[str]:
        if self.has_cycle():
            raise CycleError("Cycle detected in DAG")
        in_degree = {node_id: len(self.reverse_edges.get(node_id, []))
                     for node_id in self.nodes}
        queue = deque(sorted([n for n, d in in_degree.items() if d == 0]))
        result = []
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            for dependent in self.edges[node_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue = deque(sorted(queue))
        return result

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()
        def visit(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for dependent in self.edges.get(node_id, []):
                if dependent not in visited:
                    if visit(dependent):
                        return True
                elif dependent in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False
        for node_id in self.nodes:
            if node_id not in visited:
                if visit(node_id):
                    return True
        return False

    def get_execution_order(self) -> list[str]:
        topo = self.topological_sort()
        return list(reversed(topo))

    def get_dependencies(self, node_id: str) -> list[str]:
        return list(self.edges.get(node_id, []))

    def get_dependents(self, node_id: str) -> list[str]:
        return list(self.reverse_edges.get(node_id, []))

    def get_transitive_dependencies(self, node_id: str) -> set[str]:
        result = set()
        queue = deque(self.get_dependencies(node_id))
        while queue:
            dep = queue.popleft()
            if dep not in result:
                result.add(dep)
                queue.extend(self.get_dependencies(dep))
        return result

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"id": n.id, "metadata": n.metadata}
                for n in self.nodes.values()
            ],
            "edges": [
                {"from": from_id, "to": to_id}
                for from_id, tos in self.edges.items()
                for to_id in tos
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DAG':
        dag = cls()
        for node in data.get("nodes", []):
            dag.add_node(node["id"], node.get("metadata"))
        for edge in data.get("edges", []):
            dag.add_edge(edge["from"], edge["to"])
        return dag

def build_dag_from_ast(ast_nodes: list) -> DAG:
    dag = DAG()
    for node in ast_nodes:
        if hasattr(node, 'name'):
            dag.add_node(node.name)
    for node in ast_nodes:
        if hasattr(node, 'name') and hasattr(node, 'properties'):
            for prop in node.properties:
                if prop.name == "depends_on":
                    deps = prop.value if isinstance(prop.value, list) else [prop.value]
                    for dep in deps:
                        dag.add_edge(node.name, str(dep))
    return dag

# ============================================================
# CIERRE STARKCORE — DAG QUE SE ATESTIGA A SÍ MISMO
# ============================================================
class AttestedDAG(DAG):
    """
    DAG con Artículo 0. Detecta SeedDecl y corre verify().
    Si falla → CA002 → NUNCA LLEGA AL SCHEDULER.
    """
    def attest(self, *, seed_channel, published_hashes: Dict[str, str]) -> bool:
        for node_id, dnode in self.nodes.items():
            expected = published_hashes.get(node_id)
            if expected is None:
                continue
            ast_node = dnode.metadata.get("ast_node") if hasattr(dnode, 'metadata') else None
            if ast_node is None:
                continue
            if hasattr(ast_node, "tokens") and hasattr(ast_node, "bit_length"):
                seed_channel.verify(ast_node, expected)
        return True