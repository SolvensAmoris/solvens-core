"""
solvens/cosmos/moat_parser.py
=============================

COSMOS DAG PARSER v0.2
=====================

Parser para Cosmos DSL - El moat secreto de Solvens.

Grammar:
    universe -> galaxies -> planets -> lights (edges)
    
Example:
    cosmos
        universe ResearchAgent {
            sun CentralOrchestrator
            
            planet Researcher {
                model: claude-3-sonnet
                connects_to: Coder
            }
            
            planet Coder {
                model: gpt-4
                connects_to: Reviewer
            }
            
            planet Reviewer {
                model: gemini
            }
            
            light ResearchFlow {
                from: CentralOrchestrator
                to: [Researcher, Coder, Reviewer]
            }
        }
    end

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger("solvens.cosmos.parser")


# ============================================================
# ENUMS Y TIPOS
# ============================================================

class NodeType(Enum):
    """Tipos de nodos Cosmos."""
    UNIVERSE = "universe"
    SUN = "sun"          # Entry point
    GALAXY = "galaxy"    # Group of planets
    PLANET = "planet"    # Task/Agent
    LIGHT = "light"       # Flow/Edge
    STAR = "star"         # Provider
    CONSTRAINT = "constraint"  # Temporal/Resource constraints


@dataclass
class CosmosNode:
    """
    Nodo del grafo Cosmos.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        node_type: Type of node
        properties: Node metadata
        parents: IDs of parent nodes
        children: IDs of child nodes
        constraints: Node-level constraints
        position: Optional (x, y) for visualization
    """
    id: str
    name: str
    node_type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)
    parents: Set[str] = field(default_factory=set)
    children: Set[str] = field(default_factory=set)
    constraints: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Tuple[float, float]] = None
    
    # Computed fields
    _hash: str = field(default="", repr=False)
    
    @property
    def structural_hash(self) -> str:
        """Hash determinístico del nodo."""
        if not self._hash:
            self._compute_hash()
        return self._hash
    
    def _compute_hash(self) -> str:
        """Computa hash estructural."""
        canonical = {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "properties": dict(sorted(self.properties.items())),
        }
        canonical_str = str(sorted(canonical.items()))
        self._hash = hashlib.sha256(canonical_str.encode()).hexdigest()
        return self._hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "properties": self.properties,
            "parents": list(self.parents),
            "children": list(self.children),
            "constraints": self.constraints,
            "position": self.position,
            "hash": self.structural_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CosmosNode:
        """Deserializa desde diccionario."""
        return cls(
            id=data["id"],
            name=data["name"],
            node_type=NodeType(data.get("type", "planet")),
            properties=data.get("properties", {}),
            parents=set(data.get("parents", [])),
            children=set(data.get("children", [])),
            constraints=data.get("constraints", {}),
            position=data.get("position"),
        )


@dataclass
class CosmosEdge:
    """Arista del grafo Cosmos."""
    source: str
    target: str
    edge_type: str = "flow"  # flow, dependency, constraint
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class TemporalConstraint:
    """Restricción temporal."""
    node_id: str
    start_after: Optional[datetime] = None
    end_before: Optional[datetime] = None
    max_duration_seconds: Optional[float] = None
    depends_on: List[str] = field(default_factory=list)


# ============================================================
# PARSER
# ============================================================

class CosmosParser:
    """
    Parser para Cosmos DSL.
    
    Convierte texto Cosmos a DAG ejecutable.
    
    Usage:
        parser = CosmosParser()
        dag = parser.parse(cosmos_code)
    """
    
    # Regex patterns
    PATTERN_UNIVERSE = r'cosmos\s+(\w+)\s*\{'
    PATTERN_UNIVERSE_END = r'\}\s*end'
    PATTERN_SUN = r'sun\s+(\w+)'
    PATTERN_GALAXY = r'galaxy\s+(\w+)\s*\{([^}]*)\}'
    PATTERN_PLANET = r'planet\s+(\w+)\s*\{([^}]*)\}'
    PATTERN_LIGHT = r'light\s+(\w+)\s*\{([^}]*)\}'
    PATTERN_STAR = r'star\s+(\w+)\s*\{([^}]*)\}'
    PATTERN_CONNECT = r'connects_to:\s*\[?([^\]\n,]+)\]?'
    PATTERN_FROM = r'from:\s*\[?([^\]\n,]+)\]?'
    PATTERN_TO = r'to:\s*\[?([^\]\n,]+)\]?'
    PATTERN_MODEL = r'model:\s*(\S+)'
    PATTERN_CONSTRAINT = r'constraint\s+(\w+):\s*([^\n,]+)'
    PATTERN_PROPERTY = r'(\w+):\s*([^\n,]+)'
    
    def __init__(self):
        self.nodes: Dict[str, CosmosNode] = {}
        self.edges: List[CosmosEdge] = []
        self.universe_name: str = ""
        self.current_galaxy: Optional[str] = None
        self._constraints: List[TemporalConstraint] = []
    
    def parse(self, cosmos_text: str) -> CosmosDAG:
        """
        Parsea texto Cosmos a CosmosDAG.
        
        Args:
            cosmos_text: Código Cosmos en DSL
            
        Returns:
            CosmosDAG ejecutable
        """
        logger.info("Parsing Cosmos code")
        
        # Reset state
        self.nodes = {}
        self.edges = []
        self._constraints = []
        self.universe_name = ""
        
        # Remove comments and normalize
        lines = []
        for line in cosmos_text.strip().split('\n'):
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
        
        # Join back
        cosmos_text = '\n'.join(lines)
        
        # Find universe
        universe_match = re.search(r'cosmos\s+(\w+)\s*\{', cosmos_text)
        if universe_match:
            self.universe_name = universe_match.group(1)
            logger.info(f"Universe: {self.universe_name}")
        
        # Extract all blocks with their content
        block_pattern = r'(\w+)\s+(\w+)\s*\{([^}]*)\}'
        
        for match in re.finditer(block_pattern, cosmos_text):
            node_type_str = match.group(1)
            block_name = match.group(2)
            content = match.group(3)
            
            # Map string to enum
            type_map = {
                'sun': NodeType.SUN,
                'planet': NodeType.PLANET,
                'galaxy': NodeType.GALAXY,
                'light': NodeType.LIGHT,
                'star': NodeType.STAR,
            }
            
            node_type = type_map.get(node_type_str.lower())
            if node_type:
                self._parse_block(node_type, block_name, content)
        
        # Build edges from connections
        self._build_edges()
        
        # Create DAG
        dag = CosmosDAG(
            nodes=self.nodes,
            edges=self.edges,
            universe=self.universe_name,
            constraints=self._constraints
        )
        
        logger.info(f"Parsed {len(self.nodes)} nodes, {len(self.edges)} edges")
        
        return dag
    
    def _parse_block(self, node_type: NodeType, name: str, content: str):
        """Parsea un bloque de nodo."""
        node_id = self._normalize_id(name)
        
        # Extract properties
        properties = {}
        
        # Model
        model_match = re.search(self.PATTERN_MODEL, content)
        if model_match:
            properties["model"] = model_match.group(1)
        
        # Connects to (for planets)
        connects_match = re.search(self.PATTERN_CONNECT, content)
        if connects_match:
            targets = self._parse_list(connects_match.group(1))
            properties["connects_to"] = targets
        
        # From/To (for lights)
        from_match = re.search(self.PATTERN_FROM, content)
        to_match = re.search(self.PATTERN_TO, content)
        
        if from_match and to_match:
            properties["from"] = self._normalize_id(from_match.group(1))
            properties["to"] = [self._normalize_id(t) for t in self._parse_list(to_match.group(1))]
        
        # Generic properties
        for match in re.finditer(self.PATTERN_PROPERTY, content):
            key, value = match.groups()
            if key not in ["connects_to", "from", "to", "model"]:
                properties[key] = value.strip()
        
        # Create node
        node = CosmosNode(
            id=node_id,
            name=name,
            node_type=node_type,
            properties=properties
        )
        
        self.nodes[node_id] = node
        
        # Handle special connections
        if "connects_to" in properties:
            for target in properties["connects_to"]:
                target_id = self._normalize_id(target)
                node.children.add(target_id)
                if target_id in self.nodes:
                    self.nodes[target_id].parents.add(node_id)
        
        # Handle light connections
        if node_type == NodeType.LIGHT:
            if "from" in properties and "to" in properties:
                source = properties["from"]
                for target in properties["to"]:
                    edge = CosmosEdge(
                        source=source,
                        target=target,
                        edge_type="flow",
                        label=name
                    )
                    self.edges.append(edge)
    
    def _build_edges(self):
        """Construye aristas desde las conexiones."""
        for node_id, node in self.nodes.items():
            for child_id in node.children:
                if child_id not in self.nodes:
                    # Create implicit node
                    self.nodes[child_id] = CosmosNode(
                        id=child_id,
                        name=child_id,
                        node_type=NodeType.PLANET
                    )
                
                # Add edge if not already exists
                edge_exists = any(
                    e.source == node_id and e.target == child_id 
                    for e in self.edges
                )
                if not edge_exists:
                    self.edges.append(CosmosEdge(
                        source=node_id,
                        target=child_id,
                        edge_type="flow"
                    ))
    
    def _parse_list(self, text: str) -> List[str]:
        """Parsea lista separada por comas."""
        items = [s.strip() for s in text.split(',')]
        return [i for i in items if i]
    
    def _normalize_id(self, name: str) -> str:
        """Normaliza ID de nodo."""
        return name.lower().replace('-', '_').replace(' ', '_')


# ============================================================
# COSMOS DAG
# ============================================================

class CosmosDAG:
    """
    Grafo Cosmos con identidad estructural.
    
    Representa un workflow como DAG ejecutable.
    """
    
    def __init__(
        self,
        nodes: Dict[str, CosmosNode] = None,
        edges: List[CosmosEdge] = None,
        universe: str = "",
        constraints: List[TemporalConstraint] = None
    ):
        self.nodes = nodes or {}
        self.edges = edges or []
        self.universe = universe
        self.constraints = constraints or []
        
        # Computed fields
        self._graph_hash: str = ""
        self._layers: List[List[str]] = []
        self._canonical_form: Dict[str, Any] = {}
    
    @property
    def graph_hash(self) -> str:
        """Hash del grafo completo."""
        if not self._graph_hash:
            self._compute_hash()
        return self._graph_hash
    
    def _compute_hash(self):
        """Computa hash del grafo."""
        # Topological sort
        topo_order = self.topological_sort()
        
        # Combine node hashes
        hashes = []
        for node_id in topo_order:
            if node_id in self.nodes:
                hashes.append(self.nodes[node_id].structural_hash)
        
        combined = "|".join(hashes)
        self._graph_hash = hashlib.sha256(combined.encode()).hexdigest()
    
    @property
    def layers(self) -> List[List[str]]:
        """Capas de ejecución (nodos sin dependencias entre sí)."""
        if not self._layers:
            self._layers = self._compute_layers()
        return self._layers
    
    def _compute_layers(self) -> List[List[str]]:
        """Computa capas de ejecución."""
        layers = []
        remaining = set(self.nodes.keys())
        processed = set()
        
        while remaining:
            # Find nodes with all parents processed
            current_layer = []
            for node_id in remaining:
                node = self.nodes[node_id]
                if node.parents <= processed:
                    current_layer.append(node_id)
            
            if not current_layer:
                # Cycle or error
                break
            
            layers.append(current_layer)
            processed.update(current_layer)
            remaining -= set(current_layer)
        
        return layers
    
    def topological_sort(self) -> List[str]:
        """Orden topológico de nodos."""
        visited = set()
        result = []
        
        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            
            node = self.nodes.get(node_id)
            if node:
                for parent_id in node.parents:
                    visit(parent_id)
                result.append(node_id)
        
        for node_id in self.nodes:
            visit(node_id)
        
        return result
    
    def canonicalize(self) -> CosmosDAG:
        """
        Canonicaliza el DAG para identidad estructural.
        
        Ordena nodos y normaliza para deduplicación.
        """
        # Sort nodes by hash
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: x[1].structural_hash
        )
        
        # Rebuild with sorted order
        self.nodes = dict(sorted_nodes)
        
        # Recompute hash
        self._compute_hash()
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "universe": self.universe,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [
                {"source": e.source, "target": e.target, "type": e.edge_type, "label": e.label}
                for e in self.edges
            ],
            "constraints": [
                {"node_id": c.node_id, "start_after": str(c.start_after), "end_before": str(c.end_before)}
                for c in self.constraints
            ],
            "hash": self.graph_hash,
            "layers": self.layers,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CosmosDAG:
        """Deserializa desde diccionario."""
        nodes = {
            nid: CosmosNode.from_dict(ndata)
            for nid, ndata in data.get("nodes", {}).items()
        }
        
        edges = [
            CosmosEdge(source=e["source"], target=e["target"], edge_type=e.get("type", "flow"))
            for e in data.get("edges", [])
        ]
        
        return cls(
            nodes=nodes,
            edges=edges,
            universe=data.get("universe", ""),
        )
    
    def visualize_text(self) -> str:
        """Genera representación ASCII del DAG."""
        lines = []
        lines.append("╔══════════════════════════════════════════════════════╗")
        lines.append(f"║  🌌 {self.universe or 'Cosmos DAG':<42}║")
        lines.append("╠══════════════════════════════════════════════════════╣")
        
        for layer_idx, layer in enumerate(self.layers):
            layer_nodes = [self.nodes[nid] for nid in layer if nid in self.nodes]
            
            for node in layer_nodes:
                icon = {
                    NodeType.SUN: "☀️",
                    NodeType.PLANET: "🪐",
                    NodeType.GALAXY: "🌌",
                    NodeType.LIGHT: "💡",
                    NodeType.STAR: "⭐",
                }.get(node.node_type, "●")
                
                props = ", ".join(f"{k}={v}" for k, v in list(node.properties.items())[:2])
                lines.append(f"║  [{icon}] {node.name:<15} {props[:25]:<25} ║")
            
            if layer_idx < len(self.layers) - 1:
                lines.append("║       │                                                 ║")
        
        lines.append("╚══════════════════════════════════════════════════════╝")
        lines.append(f"  Nodes: {len(self.nodes)} | Edges: {len(self.edges)} | Hash: {self.graph_hash[:16]}")
        
        return '\n'.join(lines)


# ============================================================
# DEMO
# ============================================================

def demo():
    """Demo del parser."""
    print("=" * 60)
    print("COSMOS PARSER v0.2 - MOAT DEMO")
    print("=" * 60)
    
    cosmos_code = """
cosmos ResearchAgent {
    sun CentralOrchestrator
    
    planet Researcher {
        model: claude-3-sonnet
        connects_to: Coder
    }
    
    planet Coder {
        model: gpt-4
        connects_to: Reviewer
    }
    
    planet Reviewer {
        model: gemini
    }
    
    light ResearchFlow {
        from: CentralOrchestrator
        to: [Researcher, Coder, Reviewer]
    }
}
end
"""
    
    print("\n[Parsing Cosmos code...]")
    print(cosmos_code)
    
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    
    print("\n[Visualization]")
    print(dag.visualize_text())
    
    print("\n[JSON Output]")
    import json
    print(json.dumps(dag.to_dict(), indent=2, default=str)[:500] + "...")
    
    print("\n" + "=" * 60)
    print("COSMOS PARSER MOAT ACTIVE")
    print("Hash:", dag.graph_hash[:32])
    print("=" * 60)


if __name__ == "__main__":
    demo()
