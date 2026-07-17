"""
langgraph_adapter.py - LangGraph Compatibility Layer
===================================================

Adapt Solvens Cosmos DAG to LangGraph StateGraph for
migration and compatibility.

Usage:
    adapter = LangGraphAdapter()
    langgraph = adapter.to_langgraph(cosmos_dag)
    
    # Or from Cosmos AST
    langgraph = adapter.ast_to_langgraph(cosmos_ast)
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import inspect

try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.checkpoint import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Stub for when LangGraph is not installed
    StateGraph = None


class CosmosNodeType(Enum):
    """Node types in Cosmos."""
    TASK = "task"
    AGENT = "agent"
    PROVIDER = "provider"
    CONDITION = "condition"
    TRANSFORM = "transform"
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class CosmosNode:
    """Node in Cosmos DAG."""
    id: str
    name: str
    node_type: CosmosNodeType
    config: Dict[str, Any] = field(default_factory=dict)
    function: Optional[Callable] = None


@dataclass
class CosmosEdge:
    """Edge in Cosmos DAG."""
    source: str
    target: str
    edge_type: str = "flow"  # flow, conditional, fallback


@dataclass
class CosmosDAG:
    """Cosmos Directed Acyclic Graph."""
    nodes: List[CosmosNode] = field(default_factory=list)
    edges: List[CosmosEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateSchema:
    """Schema for LangGraph state."""
    
    def __init__(self, schema: Dict[str, type] = None):
        self.schema = schema or {}


class LangGraphAdapter:
    """
    Adapter to convert Cosmos DAG to LangGraph StateGraph.
    
    Usage:
        adapter = LangGraphAdapter()
        
        # Create LangGraph from Cosmos DAG
        graph = adapter.to_langgraph(cosmos_dag)
        
        # Run the graph
        result = await graph.ainvoke({"input": "Hello"})
    """
    
    def __init__(self, checkpointer=None):
        """
        Initialize adapter.
        
        Args:
            checkpointer: LangGraph checkpointer for persistence
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph is not installed. "
                "Install with: pip install langgraph"
            )
        
        self.checkpointer = checkpointer or MemorySaver()
        self._node_registry: Dict[str, Callable] = {}
        self._condition_registry: Dict[str, Callable] = {}
    
    def register_node(
        self,
        name: str,
        func: Callable,
        node_type: CosmosNodeType = CosmosNodeType.TASK
    ):
        """
        Register a function as a Cosmos node.
        
        Args:
            name: Node identifier
            func: Async function to execute
            node_type: Type of node
        """
        self._node_registry[name] = func
    
    def register_condition(
        self,
        name: str,
        func: Callable[[Dict], str]
    ):
        """
        Register a condition function for routing.
        
        Args:
            name: Condition identifier
            func: Function that returns next node name
        """
        self._condition_registry[name] = func
    
    def to_langgraph(
        self,
        dag: CosmosDAG,
        state_schema: Optional[Dict[str, type]] = None
    ):
        """
        Convert Cosmos DAG to LangGraph StateGraph.
        
        Args:
            dag: Cosmos DAG to convert
            state_schema: Schema for graph state
        
        Returns:
            Compiled LangGraph
        """
        # Create state schema
        if state_schema is None:
            state_schema = {"messages": list, "context": dict, "result": Any}
        
        # Create builder
        builder = StateGraph(state_schema if state_schema else object)
        
        # Register nodes
        for node in dag.nodes:
            if node.id in self._node_registry:
                builder.add_node(node.id, self._node_registry[node.id])
            elif node.function:
                builder.add_node(node.id, node.function)
            else:
                # Create wrapper for unregistered nodes
                builder.add_node(
                    node.id,
                    self._create_wrapper(node)
                )
        
        # Add edges
        for edge in dag.edges:
            if edge.edge_type == "flow":
                builder.add_edge(edge.source, edge.target)
            elif edge.edge_type == "conditional":
                # Conditional edges need special handling
                condition_func = self._condition_registry.get(edge.target)
                if condition_func:
                    builder.add_conditional_edges(
                        edge.source,
                        condition_func,
                        {edge.target: edge.target}
                    )
            elif edge.edge_type == "fallback":
                # Add edge with fallback marker
                builder.add_edge(edge.source, edge.target)
        
        # Set entry point
        entry_nodes = [n.id for n in dag.nodes if n.node_type == CosmosNodeType.INPUT]
        if entry_nodes:
            builder.set_entry_point(entry_nodes[0])
        else:
            builder.set_entry_point(dag.nodes[0].id if dag.nodes else START)
        
        # Set exit point
        exit_nodes = [n.id for n in dag.nodes if n.node_type == CosmosNodeType.OUTPUT]
        if exit_nodes:
            builder.set_finish_point(exit_nodes[-1])
        else:
            builder.add_edge(dag.nodes[-1].id if dag.nodes else START, END)
        
        # Compile with checkpointer
        graph = builder.compile(checkpointer=self.checkpointer)
        
        return graph
    
    def ast_to_langgraph(
        self,
        ast: Dict[str, Any],
        state_schema: Optional[Dict[str, type]] = None
    ) -> Any:
        """
        Convert Cosmos AST directly to LangGraph.
        
        Args:
            ast: Cosmos AST dictionary
            state_schema: Schema for graph state
        
        Returns:
            Compiled LangGraph
        """
        dag = self._ast_to_dag(ast)
        return self.to_langgraph(dag, state_schema)
    
    def _ast_to_dag(self, ast: Dict[str, Any]) -> CosmosDAG:
        """Convert Cosmos AST to DAG."""
        nodes = []
        edges = []
        
        # Process universe
        universe = ast.get("universe", {})
        name = universe.get("name", "universe")
        
        # Create nodes for each element
        elements = universe.get("elements", [])
        
        prev_node_id = None
        for i, elem in enumerate(elements):
            elem_type = elem.get("type", "task")
            elem_name = elem.get("name", f"{elem_type}_{i}")
            elem_id = elem.get("id", elem_name.lower().replace(" ", "_"))
            
            # Map Cosmos type to CosmosNodeType
            node_type_map = {
                "light": CosmosNodeType.TASK,
                "celestial_body": CosmosNodeType.AGENT,
                "event": CosmosNodeType.PROVIDER,
                "constraint": CosmosNodeType.CONDITION,
                "transform": CosmosNodeType.TRANSFORM,
            }
            node_type = node_type_map.get(elem_type, CosmosNodeType.TASK)
            
            nodes.append(CosmosNode(
                id=elem_id,
                name=elem_name,
                node_type=node_type,
                config=elem
            ))
            
            # Create flow edges
            if prev_node_id:
                edges.append(CosmosEdge(
                    source=prev_node_id,
                    target=elem_id,
                    edge_type="flow"
                ))
            
            prev_node_id = elem_id
        
        return CosmosDAG(
            nodes=nodes,
            edges=edges,
            metadata={"name": name}
        )
    
    def _create_wrapper(self, node: CosmosNode) -> Callable:
        """Create wrapper function for unregistered nodes."""
        
        async def wrapper(state: Dict) -> Dict:
            # Simple pass-through with logging
            if "messages" in state:
                last_msg = state["messages"][-1] if state["messages"] else {}
                content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
                print(f"[Cosmos:node:{node.id}] Processing: {content[:50]}...")
            
            # Pass state through
            return state
        
        return wrapper


# ============================================================
# Migration Utilities
# ============================================================

def create_migration_guide() -> str:
    """
    Generate a migration guide from LangGraph to Solvens Cosmos.
    
    Returns:
        Markdown migration guide
    """
    return '''# LangGraph to Solvens Cosmos Migration Guide

## Quick Reference

| LangGraph Concept | Cosmos Equivalent |
|------------------|-------------------|
| `StateGraph` | `CosmosDAG` |
| `add_node()` | `CosmosNode` |
| `add_edge()` | `CosmosEdge` |
| `add_conditional_edges()` | `edge_type="conditional"` |
| `checkpointer` | `Checkpoint` (planned) |
| `@entrypoint` | `CosmosNode(type="input")` |
| `END` | `CosmosNode(type="output")` |

## Example Conversion

### LangGraph Code

```python
from langgraph.graph import StateGraph, END

def should_continue(state):
    return "continue" if state["count"] < 5 else END

workflow = StateGraph(State)
workflow.add_node("agent", agent_node)
workflow.add_node("action", action_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("action", "agent")
workflow.add_edge("action", END)

app = workflow.compile()
```

### Cosmos Equivalent

```python
from solvens.cosmos import DAG, Node, Edge

dag = DAG(
    nodes=[
        Node(id="agent", name="Agent", type="task"),
        Node(id="action", name="Action", type="task"),
    ],
    edges=[
        Edge(source="__start__", target="agent", type="flow"),
        Edge(source="agent", target="action", type="conditional", condition="should_continue"),
        Edge(source="action", target="agent", type="flow"),
        Edge(source="action", target="__end__", type="flow"),
    ]
)
```

## Key Differences

1. **State Management**: LangGraph uses typed schemas, Cosmos uses dynamic dicts
2. **Conditional Routing**: LangGraph uses functions, Cosmos uses edge conditions
3. **Persistence**: LangGraph has mature checkpointing, Cosmos is planned
4. **Visualization**: Cosmos has built-in DAG visualization

## Recommended Migration Path

1. **Phase 1**: Use `LangGraphAdapter` to run existing LangGraph in Cosmos
2. **Phase 2**: Gradually convert nodes to Cosmos format
3. **Phase 3**: Enable Cosmos visualization and tracing
4. **Phase 4**: Use Cosmos-specific features (multi-provider routing, etc.)

## Running LangGraph in Cosmos

```python
from solvens.compat import LangGraphAdapter

adapter = LangGraphAdapter()

# Register your LangGraph functions
adapter.register_node("agent", my_agent_function)
adapter.register_node("action", my_action_function)

# Convert from existing LangGraph
langgraph = adapter.to_langgraph(cosmos_dag)

# Or create new with adapter
adapter.register_node("task1", task1_func)
adapter.register_node("task2", task2_func)
# ... then build graph normally
```
'''


# ============================================================
# Demo
# ============================================================

def demo():
    """Demo del LangGraph adapter."""
    print("=" * 60)
    print("LANGGRAPH ADAPTER DEMO")
    print("=" * 60)
    
    if not LANGGRAPH_AVAILABLE:
        print("\n⚠️  LangGraph not installed")
        print("   Install with: pip install langgraph")
        print("\n   Generating migration guide anyway...")
        print("\n" + create_migration_guide())
        return
    
    # Create Cosmos DAG
    dag = CosmosDAG(
        nodes=[
            CosmosNode("input", "User Input", CosmosNodeType.INPUT),
            CosmosNode("router", "Router", CosmosNodeType.TASK),
            CosmosNode("claude", "Claude Agent", CosmosNodeType.AGENT),
            CosmosNode("gpt", "GPT Agent", CosmosNodeType.AGENT),
            CosmosNode("output", "Output", CosmosNodeType.OUTPUT),
        ],
        edges=[
            CosmosEdge("input", "router"),
            CosmosEdge("router", "claude", "conditional"),
            CosmosEdge("router", "gpt", "conditional"),
            CosmosEdge("claude", "output"),
            CosmosEdge("gpt", "output"),
        ],
        metadata={"name": "Multi-Provider Router"}
    )
    
    # Create adapter
    adapter = LangGraphAdapter()
    
    # Register node functions
    async def router_node(state):
        print("  [Router] Deciding provider...")
        return {"route": "claude"}
    
    async def claude_node(state):
        print("  [Claude] Generating response...")
        return {"response": "Claude's response"}
    
    async def gpt_node(state):
        print("  [GPT] Generating response...")
        return {"response": "GPT's response"}
    
    adapter.register_node("router", router_node)
    adapter.register_node("claude", claude_node)
    adapter.register_node("gpt", gpt_node)
    
    # Convert to LangGraph
    print("\n[Converting Cosmos DAG to LangGraph...]")
    graph = adapter.to_langgraph(dag)
    
    print(f"  Graph created: {graph}")
    print(f"  Nodes: {len(dag.nodes)}")
    print(f"  Edges: {len(dag.edges)}")
    
    # Show migration guide
    print("\n[Migration Guide Preview]")
    guide = create_migration_guide()
    print(guide[:500] + "...")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
