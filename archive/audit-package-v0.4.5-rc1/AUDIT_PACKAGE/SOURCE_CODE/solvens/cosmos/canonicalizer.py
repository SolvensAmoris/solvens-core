"""Cosmos Canonicalizer module.

Normalizes AST structures to create canonical representations.
Ensures structural identity regardless of input order or formatting.
"""

from __future__ import annotations

from typing import Any

from solvens.cosmos.ast import CosmosAST, CosmosNode, CosmosNodeType


class CosmosCanonicalizer:
    """Canonicalizes Cosmos AST structures.
    
    The canonicalizer ensures:
    - Deterministic ordering of nodes
    - Removal of duplicates
    - Structural identity preservation
    - Hash generation for comparison
    """
    
    def __init__(self):
        self._visited: set[str] = set()
    
    def canonicalize(self, ast: CosmosAST) -> CosmosAST:
        """Canonicalize an AST.
        
        Returns a new AST with:
        - Sorted children
        - Deduplicated nodes
        - Updated canonical hashes
        """
        # Create a copy to avoid modifying the original
        canonical = CosmosAST()
        
        # Process root and all descendants
        self._process_node(ast.root, canonical.root)
        
        # Rebuild indices
        for node_id, node in ast.nodes.items():
            if node_id not in self._visited:
                canonical.nodes[node_id] = node
        
        return canonical
    
    def _process_node(self, source: CosmosNode, target: CosmosNode) -> None:
        """Process a single node and its children."""
        self._visited.add(source.id)
        
        # Sort children by type and name
        for relation, children in source.relations.items():
            sorted_children = sorted(
                children,
                key=lambda c: (c.node_type.value, c.properties.get("name", ""))
            )
            
            for child in sorted_children:
                # Skip duplicates (same canonical hash)
                if self._is_duplicate(child):
                    continue
                
                new_child = CosmosNode(
                    node_type=child.node_type,
                    properties=child.properties.copy(),
                    metadata=child.metadata.copy(),
                )
                
                target.add_child(relation, new_child)
                self._process_node(child, new_child)
        
        # Update canonical hash
        target._update_canonical_hash()
    
    def _is_duplicate(self, node: CosmosNode) -> bool:
        """Check if a node is a duplicate based on canonical hash."""
        for existing in self._visited:
            if existing == node.canonical_hash:
                return True
        return False
    
    def compute_identity(self, ast: CosmosAST) -> str:
        """Compute a single identity hash for the entire AST.
        
        This can be used for:
        - Caching
        - Deduplication
        - Comparison
        """
        nodes_hashes = []
        for node in self._get_sorted_nodes(ast.root):
            nodes_hashes.append(node.canonical_hash)
        
        return "|".join(nodes_hashes)
    
    def _get_sorted_nodes(self, node: CosmosNode) -> list[CosmosNode]:
        """Get all nodes in deterministic order."""
        result = []
        
        def traverse(n: CosmosNode) -> None:
            result.append(n)
            for children in n.relations.values():
                for child in sorted(children, key=lambda c: c.canonical_hash):
                    traverse(child)
        
        traverse(node)
        return result
    
    def merge(self, ast1: CosmosAST, ast2: CosmosAST) -> CosmosAST:
        """Merge two ASTs, keeping canonical form.
        
        Nodes with the same canonical hash are considered duplicates.
        """
        merged = CosmosAST()
        seen_hashes: set[str] = set()
        
        for node in self._get_sorted_nodes(ast1.root):
            if node.canonical_hash not in seen_hashes:
                merged.nodes[node.id] = node
                seen_hashes.add(node.canonical_hash)
        
        for node in self._get_sorted_nodes(ast2.root):
            if node.canonical_hash not in seen_hashes:
                merged.nodes[node.id] = node
                seen_hashes.add(node.canonical_hash)
        
        return merged
    
    def diff(self, ast1: CosmosAST, ast2: CosmosAST) -> dict[str, Any]:
        """Compare two ASTs and return differences.
        
        Returns:
            Dictionary with added, removed, and modified nodes
        """
        hash1 = {node.canonical_hash: node for node in self._get_sorted_nodes(ast1.root)}
        hash2 = {node.canonical_hash: node for node in self._get_sorted_nodes(ast2.root)}
        
        hashes1 = set(hash1.keys())
        hashes2 = set(hash2.keys())
        
        return {
            "added": [
                hash2[h].to_dict() 
                for h in hashes2 - hashes1
                if h in hash2
            ],
            "removed": [
                hash1[h].to_dict() 
                for h in hashes1 - hashes2
                if h in hash1
            ],
            "common": len(hashes1 & hashes2),
            "total_changes": len(hashes1 ^ hashes2),
        }
