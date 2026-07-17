"""Cosmos Planner module.

Transforms DAG into executable subtasks.
Determines execution order, parallelism, and resource allocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from solvens.cosmos.ast import CosmosAST, CosmosNode, CosmosNodeType
from solvens.cosmos.dag import CosmosDAG, DAGNode, DAGEdge, DAGEdgeType, DAGNodeStatus


class CosmosPlanner:
    """Plans execution of Cosmos DAG.
    
    The planner:
    - Decomposes large tasks into subtasks
    - Determines execution order
    - Identifies parallelization opportunities
    - Estimates costs and resources
    - Assigns providers/agents/tools
    """
    
    # Provider recommendations based on operation type
    PROVIDER_HINTS = {
        "code": "anthropic",
        "analysis": "openai",
        "research": "google",
        "reasoning": "openai",
        "creative": "grok",
        "translation": "deepseek",
        "offline": "ollama",
    }
    
    def __init__(self):
        self.execution_plan: ExecutionPlan | None = None
    
    def plan(self, ast_or_dag: CosmosAST | CosmosDAG) -> ExecutionPlan:
        """Create an execution plan from an AST or DAG.
        
        Flow:
        AST/DAG → Optimize → Execution Plan
        """
        # If it's a DAG, use it directly
        if isinstance(ast_or_dag, CosmosDAG):
            dag = ast_or_dag
        else:
            # Transform AST to DAG
            dag = self._ast_to_dag(ast_or_dag)
        
        # Analyze DAG for optimization
        optimized_dag = self._optimize_dag(dag)
        
        # Generate execution plan
        plan = self._generate_plan(optimized_dag)
        
        self.execution_plan = plan
        return plan
    
    def _ast_to_dag(self, ast: CosmosAST) -> CosmosDAG:
        """Convert AST to DAG representation."""
        dag = CosmosDAG()
        
        # Process each node in the AST
        for node in ast.get_all_nodes():
            dag_node = self._convert_node_to_dag_node(node)
            dag.add_node(dag_node)
        
        # Add edges based on AST relations
        for node in ast.get_all_nodes():
            for relation, children in node.relations.items():
                for child in children:
                    edge = DAGEdge(
                        source_id=node.id,
                        target_id=child.id,
                        edge_type=self._relation_to_edge_type(relation),
                    )
                    dag.add_edge(edge)
        
        return dag
    
    def _convert_node_to_dag_node(self, ast_node: CosmosNode) -> DAGNode:
        """Convert an AST node to a DAG node."""
        # Determine operation type
        operation = self._determine_operation(ast_node)
        
        # Get provider recommendation
        provider = self._recommend_provider(ast_node)
        
        # Estimate cost and duration
        cost, duration = self._estimate_metrics(ast_node)
        
        dag_node = DAGNode(
            id=ast_node.id,
            name=ast_node.properties.get("name", ""),
            node_type=ast_node.node_type.value,
            operation=operation,
            provider=provider,
            tool=ast_node.properties.get("tool"),
            priority=ast_node.properties.get("priority", 50),
            estimated_cost=cost,
            estimated_duration=duration,
            properties=ast_node.properties,
            metadata=ast_node.metadata,
        )
        
        return dag_node
    
    def _determine_operation(self, node: CosmosNode) -> str:
        """Determine the operation type for a node."""
        node_type = node.node_type
        
        operation_map = {
            CosmosNodeType.TASK: "execute_task",
            CosmosNodeType.ACTION: "perform_action",
            CosmosNodeType.QUERY: "answer_query",
            CosmosNodeType.TRANSFORM: "transform_data",
            CosmosNodeType.SEQUENCE: "execute_sequence",
            CosmosNodeType.PARALLEL: "execute_parallel",
            CosmosNodeType.CONDITIONAL: "evaluate_condition",
            CosmosNodeType.AGENT: "invoke_agent",
            CosmosNodeType.TOOL: "use_tool",
        }
        
        return operation_map.get(node_type, "generic_operation")
    
    def _recommend_provider(self, node: CosmosNode) -> str | None:
        """Recommend a provider based on node characteristics."""
        name = node.properties.get("name", "").lower()
        props = str(node.properties).lower()
        
        for keyword, provider in self.PROVIDER_HINTS.items():
            if keyword in name or keyword in props:
                return provider
        
        return None
    
    def _estimate_metrics(self, node: CosmosNode) -> tuple[float, float]:
        """Estimate cost and duration for a node."""
        # Simple heuristics
        node_type = node.node_type
        
        base_costs = {
            CosmosNodeType.TASK: (1.0, 10.0),
            CosmosNodeType.ACTION: (0.5, 5.0),
            CosmosNodeType.QUERY: (0.3, 3.0),
            CosmosNodeType.TRANSFORM: (0.8, 8.0),
            CosmosNodeType.SEQUENCE: (2.0, 20.0),
            CosmosNodeType.PARALLEL: (3.0, 15.0),
        }
        
        base_cost, base_duration = base_costs.get(node_type, (1.0, 10.0))
        
        # Adjust based on properties
        priority = node.properties.get("priority", 50)
        priority_factor = priority / 50.0
        
        return base_cost * priority_factor, base_duration * priority_factor
    
    def _relation_to_edge_type(self, relation: str) -> DAGEdgeType:
        """Convert AST relation to DAG edge type."""
        mapping = {
            "depends_on": DAGEdgeType.DEPENDENCY,
            "produces": DAGEdgeType.DATA_FLOW,
            "controls": DAGEdgeType.CONTROL_FLOW,
            "references": DAGEdgeType.REFERENCE,
        }
        return mapping.get(relation, DAGEdgeType.DEPENDENCY)
    
    def _optimize_dag(self, dag: CosmosDAG) -> CosmosDAG:
        """Optimize the DAG for execution."""
        # Remove redundant dependencies
        optimized = self._remove_redundant_edges(dag)
        
        # Merge similar nodes
        optimized = self._merge_similar_nodes(optimized)
        
        return optimized
    
    def _remove_redundant_edges(self, dag: CosmosDAG) -> CosmosDAG:
        """Remove edges that are transitively implied."""
        # Build transitive closure
        transitive = self._compute_transitive_closure(dag)
        
        # Remove redundant edges
        edges_to_remove = []
        for edge_id, edge in dag.edges.items():
            # If there's a transitive path, this direct edge may be redundant
            if self._is_transitive_path(dag, edge.source_id, edge.target_id, transitive):
                edges_to_remove.append(edge_id)
        
        for edge_id in edges_to_remove:
            del dag.edges[edge_id]
        
        return dag
    
    def _compute_transitive_closure(self, dag: CosmosDAG) -> dict[str, set[str]]:
        """Compute transitive closure of the DAG."""
        closure: dict[str, set[str]] = {node_id: set() for node_id in dag.nodes}
        
        # Find all reachable nodes from each node
        for node_id in dag.nodes:
            visited = set()
            stack = [node_id]
            
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                
                visited.add(current)
                for dependent_id in dag.nodes[current].dependents:
                    if dependent_id not in visited:
                        closure[node_id].add(dependent_id)
                        stack.append(dependent_id)
        
        return closure
    
    def _is_transitive_path(
        self, 
        dag: CosmosDAG, 
        source: str, 
        target: str, 
        transitive: dict[str, set[str]]
    ) -> bool:
        """Check if path between source and target is transitive."""
        return target in transitive.get(source, set())
    
    def _merge_similar_nodes(self, dag: CosmosDAG) -> CosmosDAG:
        """Merge nodes with identical operations and dependencies."""
        # Group nodes by operation and dependencies
        groups: dict[str, list[str]] = {}
        
        for node_id, node in dag.nodes.items():
            key = self._get_merge_key(node)
            if key not in groups:
                groups[key] = []
            groups[key].append(node_id)
        
        # Merge nodes in each group (simplified - just flag for now)
        return dag
    
    def _get_merge_key(self, node: DAGNode) -> str:
        """Get a key for merging similar nodes."""
        return f"{node.operation}|{len(node.dependencies)}"
    
    def _generate_plan(self, dag: CosmosDAG) -> ExecutionPlan:
        """Generate an execution plan from the DAG."""
        plan = ExecutionPlan(dag_id=dag.id)
        
        # Get parallelizable layers
        layers = dag.get_parallelizable_nodes()
        
        for layer_idx, layer in enumerate(layers):
            phase = ExecutionPhase(
                phase_id=f"phase_{layer_idx}",
                order=layer_idx,
                nodes=[node.id for node in layer],
            )
            
            # Set parallel flag for layers with multiple nodes
            if len(layer) > 1:
                phase.parallel = True
            
            # Set estimated duration for phase
            phase.estimated_duration = max(
                (n.estimated_duration for n in layer), default=0.0
            )
            
            plan.phases.append(phase)
        
        # Set total estimates
        plan.total_cost = sum(p.cost for p in plan.phases)
        plan.total_duration = sum(p.estimated_duration for p in plan.phases)
        
        return plan


class PhaseStatus(Enum):
    """Status of an execution phase."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExecutionPhase:
    """Represents a phase in the execution plan."""
    
    phase_id: str
    order: int
    nodes: list[str]  # Node IDs
    parallel: bool = False
    estimated_duration: float = 0.0
    cost: float = 0.0
    status: PhaseStatus = PhaseStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass 
class ExecutionPlan:
    """Complete execution plan for a Cosmos DAG."""
    
    dag_id: str
    phases: list[ExecutionPhase] = field(default_factory=list)
    total_cost: float = 0.0
    total_duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "order": p.order,
                    "nodes": p.nodes,
                    "parallel": p.parallel,
                    "estimated_duration": p.estimated_duration,
                    "cost": p.cost,
                    "status": p.status.value,
                }
                for p in self.phases
            ],
            "total_cost": self.total_cost,
            "total_duration": self.total_duration,
            "metadata": self.metadata,
        }
