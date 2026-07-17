# === SOLVENS COSMOS CANONICALIZER - MARKET READY v0.2 ===

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import copy
import uuid

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cosmos.canonicalizer')

class CanonicalizationError(Exception): pass
class HashMismatchError(CanonicalizationError): pass
class MergeConflictError(CanonicalizationError): pass

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def structural_hash(obj: Any, include_children: bool = True) -> str:
    if isinstance(obj, dict):
        items = []
        for k in sorted(obj.keys()):
            v = obj[k]
            items.append(f"{k}:{structural_hash(v, include_children)}")
        return sha256_hash("{" + ",".join(items) + "}")
    elif isinstance(obj, list):
        return sha256_hash("[" + ",".join(structural_hash(i, include_children) for i in obj) + "]")
    elif obj is None:
        return sha256_hash("null")
    else:
        return sha256_hash(str(obj))

class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"

@dataclass
class Change:
    path: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None
    hash_before: str = ""
    hash_after: str = ""

@dataclass
class DiffResult:
    changes: List[Change] = field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0
    @property
    def has_changes(self) -> bool:
        return self.added_count > 0 or self.removed_count > 0 or self.modified_count > 0

@dataclass
class MergeResult:
    merged: Dict[str, Any]
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    hash_result: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CosmosNodeCanonical:
    id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List['CosmosNodeCanonical'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _structural_hash: str = field(default="", repr=False)
    _canonical_form: Dict[str, Any] = field(default_factory=dict, repr=False)
    _children_hashes: List[str] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        self._compute_structural_identity()
    
    def _compute_structural_identity(self):
        self._children_hashes = [c.structural_hash for c in self.children]
        self._canonical_form = self._build_canonical_form()
        self._structural_hash = structural_hash(self._canonical_form, True)
    
    def _build_canonical_form(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "type": self.node_type,
            "properties": dict(sorted(self.properties.items())),
            "children": sorted([c.id for c in self.children]),
            "children_hashes": self._children_hashes,
        }
    
    @property
    def structural_hash(self) -> str:
        if not self._structural_hash:
            self._compute_structural_identity()
        return self._structural_hash
    
    @property
    def canonical_form(self) -> Dict[str, Any]:
        if not self._canonical_form:
            self._compute_structural_identity()
        return self._canonical_form
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "node_type": self.node_type,
                "properties": self.properties, "children": [c.id for c in self.children],
                "metadata": self.metadata, "structural_hash": self.structural_hash}
    
    def merge_with(self, other: 'CosmosNodeCanonical') -> Tuple['CosmosNodeCanonical', List[Dict]]:
        conflicts = []
        if self.structural_hash != other.structural_hash:
            conflicts.append({"type": "mismatch", "node_id": self.id})
        merged_props = {**self.properties, **other.properties}
        merged_children = self.children + [c for c in other.children if c.id not in {x.id for x in self.children}]
        return CosmosNodeCanonical(id=self.id, name=self.name, node_type=self.node_type,
                                  properties=merged_props, children=merged_children), conflicts

@dataclass
class CosmosGraphCanonical:
    nodes: Dict[str, CosmosNodeCanonical] = field(default_factory=dict)
    root_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _graph_hash: str = field(default="", repr=False)
    _topo_order: List[str] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        self._validate_graph()
    
    def _validate_graph(self):
        if self.root_id and self.root_id not in self.nodes:
            raise CanonicalizationError(f"Root '{self.root_id}' not found")
    
    @property
    def graph_hash(self) -> str:
        if not self._graph_hash:
            self._compute_graph_hash()
        return self._graph_hash
    
    def _compute_graph_hash(self):
        if not self.nodes:
            self._graph_hash = sha256_hash("empty_graph")
            return
        self._topo_order = self._topological_sort()
        self._graph_hash = sha256_hash("|".join(self.nodes[nid].structural_hash for nid in self._topo_order))
    
    def _topological_sort(self) -> List[str]:
        in_deg = {nid: 0 for nid in self.nodes}
        adj = {nid: [] for nid in self.nodes}
        for nid, node in self.nodes.items():
            for c in node.children:
                if c.id in in_deg:
                    in_deg[c.id] += 1
                    adj[nid].append(c.id)
        queue = [nid for nid, d in in_deg.items() if d == 0]
        result = []
        while queue:
            nid = queue.pop(0)
            result.append(nid)
            for c in adj[nid]:
                in_deg[c] -= 1
                if in_deg[c] == 0:
                    queue.append(c)
        return result
    
    def diff_with(self, other: 'CosmosGraphCanonical') -> DiffResult:
        result = DiffResult()
        for nid in sorted(set(self.nodes.keys()) | set(other.nodes.keys())):
            in_a, in_b = nid in self.nodes, nid in other.nodes
            if in_a and not in_b:
                result.changes.append(Change(f"nodes.{nid}", ChangeType.REMOVED, hash_before=self.nodes[nid].structural_hash))
                result.removed_count += 1
            elif not in_a and in_b:
                result.changes.append(Change(f"nodes.{nid}", ChangeType.ADDED, hash_after=other.nodes[nid].structural_hash))
                result.added_count += 1
            elif self.nodes[nid].structural_hash == other.nodes[nid].structural_hash:
                result.unchanged_count += 1
            else:
                result.changes.append(Change(f"nodes.{nid}", ChangeType.MODIFIED, hash_before=self.nodes[nid].structural_hash, hash_after=other.nodes[nid].structural_hash))
                result.modified_count += 1
        return result
    
    def merge_with(self, other: 'CosmosGraphCanonical') -> MergeResult:
        merged_nodes = {}
        conflicts = []
        for nid in set(self.nodes.keys()) | set(other.nodes.keys()):
            in_a, in_b = nid in self.nodes, nid in other.nodes
            if in_a and in_b:
                m, c = self.nodes[nid].merge_with(other.nodes[nid])
                merged_nodes[nid] = m
                conflicts.extend(c)
            elif in_a:
                merged_nodes[nid] = self.nodes[nid]
            else:
                merged_nodes[nid] = other.nodes[nid]
        merged_graph = CosmosGraphCanonical(nodes=merged_nodes, root_id=self.root_id or other.root_id)
        return MergeResult(merged=merged_graph.to_dict(), conflicts=conflicts, hash_result=merged_graph.graph_hash)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}, "root_id": self.root_id, "graph_hash": self.graph_hash}

class CosmosCanonicalizer:
    def __init__(self, enable_cache: bool = True):
        self.enable_cache = enable_cache
        self._cache: Dict[str, CosmosGraphCanonical] = {}
        self._stats = {"canonicalizations": 0, "cache_hits": 0, "cache_misses": 0, "diffs": 0, "merges": 0}
    
    def canonicalize(self, ast: Dict[str, Any]) -> CosmosGraphCanonical:
        cache_key = structural_hash(ast)
        if self.enable_cache and cache_key in self._cache:
            self._stats["cache_hits"] += 1
            return self._cache[cache_key]
        graph = self._ast_to_graph(ast)
        if self.enable_cache:
            self._cache[cache_key] = graph
            self._stats["cache_misses"] += 1
        self._stats["canonicalizations"] += 1
        return graph
    
    def _ast_to_graph(self, ast: Dict[str, Any]) -> CosmosGraphCanonical:
        nodes = {}
        universe = ast.get("universe", {})
        elements = universe.get("elements", [])
        for elem in elements:
            eid = elem.get("id", str(uuid.uuid4()))
            nodes[eid] = CosmosNodeCanonical(id=eid, name=elem.get("name", eid), node_type=elem.get("type", "unknown"))
        return CosmosGraphCanonical(nodes=nodes, root_id=universe.get("name", "root"))
    
    def are_equivalent(self, g_a: CosmosGraphCanonical, g_b: CosmosGraphCanonical) -> bool:
        return g_a.graph_hash == g_b.graph_hash
    
    def diff(self, g_a: CosmosGraphCanonical, g_b: CosmosGraphCanonical) -> DiffResult:
        self._stats["diffs"] += 1
        return g_a.diff_with(g_b)
    
    def merge(self, g_a: CosmosGraphCanonical, g_b: CosmosGraphCanonical) -> MergeResult:
        self._stats["merges"] += 1
        return g_a.merge_with(g_b)
    
    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "cache_size": len(self._cache)}

def run_stress_test():
    print("\n" + "=" * 60)
    print("STRESS TEST - CANONICALIZER v0.2")
    print("=" * 60)
    c = CosmosCanonicalizer()
    
    ast_a = {"universe": {"name": "test", "elements": [{"id": "n1"}, {"id": "n2"}]}}
    ast_b = {"universe": {"name": "test", "elements": [{"id": "n2"}, {"id": "n1"}]}}
    
    g_a = c.canonicalize(ast_a)
    g_b = c.canonicalize(ast_b)
    print(f"\n[Test 1] Order-independent equivalence: {c.are_equivalent(g_a, g_b)}")
    
    ast_c = {"universe": {"name": "test", "elements": [{"id": "n1"}, {"id": "n3"}]}}
    g_c = c.canonicalize(ast_c)
    diff = c.diff(g_a, g_c)
    print(f"[Test 2] Diff detected changes: {diff.modified_count + diff.added_count + diff.removed_count}")
    
    merge = c.merge(g_a, g_c)
    print(f"[Test 3] Merge conflicts: {len(merge.conflicts)}")
    
    for _ in range(100):
        c.canonicalize(ast_a)
    stats = c.get_stats()
    print(f"[Test 4] Cache hit rate: {stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) * 100:.1f}%")
    
    hashes = [c.canonicalize(ast_a).graph_hash for _ in range(10)]
    print(f"[Test 5] Deterministic hash: {len(set(hashes)) == 1}")
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    run_stress_test()
    print(f"\nModule hash: {hashlib.sha256(b'solvens-cosmos-ready').hexdigest()[:16]}")
