"""Cosmos Integration Demo.

Demonstrates the complete flow:
User Input → Parser → AST → Canonicalizer → DAG → Planner → Runtime → Result
"""

from solvens.cosmos import (
    CosmosParser,
    CosmosCanonicalizer,
    CosmosPlanner,
    CosmosRuntime,
    CosmosDAG,
    DAGNode,
    DAGEdge,
)


def demo_dsl_parsing():
    """Demo: Parse DSL Cosmos code."""
    print("=" * 60)
    print("DEMO 1: DSL Parsing")
    print("=" * 60)
    
    dsl_code = """
task: create_user_report
    provider = anthropic
    priority = 80
    
    task: fetch_data
        tool = database_query
        
    parallel: analysis
        task: calculate_metrics
            tool = python
            priority = 70
        task: generate_charts
            tool = matplotlib
    """
    
    parser = CosmosParser()
    result = parser.parse(dsl_code)
    
    print(f"Success: {result.success}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    
    if result.ast:
        print(f"Nodes in AST: {len(result.ast.nodes)}")
        for node in result.ast.get_all_nodes():
            print(f"  - {node.node_type.value}: {node.properties.get('name', 'unnamed')}")
    
    print()
    return result.ast


def demo_json_parsing():
    """Demo: Parse JSON Cosmos."""
    print("=" * 60)
    print("DEMO 2: JSON Parsing")
    print("=" * 60)
    
    json_code = """
{
    "root": {
        "type": "program",
        "properties": {"name": "json_task"},
        "relations": {
            "tasks": [
                {
                    "type": "task",
                    "properties": {"name": "step1", "provider": "openai"}
                },
                {
                    "type": "task",
                    "properties": {"name": "step2", "provider": "anthropic"}
                }
            ]
        }
    }
}
"""
    
    parser = CosmosParser()
    result = parser.parse(json_code, format=parser.parse.__code__.co_consts[0] if hasattr(parser.parse, '__code__') else None)
    
    # Use JSON format explicitly
    from solvens.cosmos.parser import InputFormat
    result = parser.parse(json_code, format=InputFormat.JSON)
    
    print(f"Success: {result.success}")
    if result.ast:
        print(f"Nodes in AST: {len(result.ast.nodes)}")
    
    print()
    return result.ast


def demo_dag_construction():
    """Demo: Build and analyze a DAG."""
    print("=" * 60)
    print("DEMO 3: DAG Construction")
    print("=" * 60)
    
    dag = CosmosDAG()
    
    # Create nodes
    fetch = DAGNode(
        name="fetch_data",
        node_type="task",
        operation="fetch_data",
        provider="database"
    )
    process = DAGNode(
        name="process_data",
        node_type="task",
        operation="process_data",
        dependencies=[fetch.id]
    )
    analyze = DAGNode(
        name="analyze_data",
        node_type="task",
        operation="analyze_data",
        dependencies=[process.id]
    )
    report = DAGNode(
        name="generate_report",
        node_type="task",
        operation="generate_report",
        dependencies=[analyze.id]
    )
    
    # Add nodes to DAG
    dag.add_node(fetch)
    dag.add_node(process)
    dag.add_node(analyze)
    dag.add_node(report)
    
    # Add edges
    dag.add_edge(DAGEdge(source_id=fetch.id, target_id=process.id))
    dag.add_edge(DAGEdge(source_id=process.id, target_id=analyze.id))
    dag.add_edge(DAGEdge(source_id=analyze.id, target_id=report.id))
    
    print(f"DAG Statistics:")
    stats = dag.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print()
    print("Topological Order:")
    for node in dag.topological_sort():
        print(f"  - {node.name}")
    
    print()
    print("Parallelizable Layers:")
    for i, layer in enumerate(dag.get_parallelizable_nodes()):
        print(f"  Layer {i}: {[n.name for n in layer]}")
    
    print()
    return dag


def demo_planning():
    """Demo: Create execution plan from DAG."""
    print("=" * 60)
    print("DEMO 4: Execution Planning")
    print("=" * 60)
    
    dag = CosmosDAG()
    
    # Create a simple pipeline
    nodes = [
        ("fetch", "fetch_data", "openai"),
        ("validate", "validate_data", "openai"),
        ("transform", "transform_data", "anthropic"),
        ("analyze", "analyze_data", "anthropic"),
        ("report", "generate_report", "grok"),
    ]
    
    dag_nodes = {}
    for name, op, provider in nodes:
        node = DAGNode(
            name=name,
            node_type="task",
            operation=op,
            provider=provider
        )
        dag.add_node(node)
        dag_nodes[name] = node
    
    # Create dependencies
    edges = [
        ("fetch", "validate"),
        ("validate", "transform"),
        ("transform", "analyze"),
        ("analyze", "report"),
    ]
    
    for source, target in edges:
        dag.add_edge(DAGEdge(source_id=dag_nodes[source].id, target_id=dag_nodes[target].id))
    
    # Plan execution
    planner = CosmosPlanner()
    plan = planner.plan(dag)
    
    print(f"Execution Plan:")
    print(f"  Total Phases: {len(plan.phases)}")
    print(f"  Estimated Cost: {plan.total_cost:.2f}")
    print(f"  Estimated Duration: {plan.total_duration:.2f}s")
    
    for phase in plan.phases:
        print(f"\n  Phase {phase.order}:")
        print(f"    Nodes: {phase.nodes}")
        print(f"    Parallel: {phase.parallel}")
        print(f"    Duration: {phase.estimated_duration:.2f}s")
    
    print()
    return plan


def demo_canonicalization():
    """Demo: Canonicalize AST for deduplication."""
    print("=" * 60)
    print("DEMO 5: AST Canonicalization")
    print("=" * 60)
    
    from solvens.cosmos import CosmosAST, CosmosNode, CosmosNodeType
    
    # Create two equivalent ASTs with different ordering
    ast1 = CosmosAST()
    node_a = CosmosNode(node_type=CosmosNodeType.TASK, properties={"name": "task_a"})
    node_b = CosmosNode(node_type=CosmosNodeType.TASK, properties={"name": "task_b"})
    ast1.add_node(node_a)
    ast1.add_node(node_b, node_a, "next")
    
    ast2 = CosmosAST()
    node_c = CosmosNode(node_type=CosmosNodeType.TASK, properties={"name": "task_b"})
    node_d = CosmosNode(node_type=CosmosNodeType.TASK, properties={"name": "task_a"})
    ast2.add_node(node_c)
    ast2.add_node(node_d, node_c, "next")
    
    # Canonicalize
    canonicalizer = CosmosCanonicalizer()
    
    print(f"AST1 hash: {canonicalizer.compute_identity(ast1)}")
    print(f"AST2 hash: {canonicalizer.compute_identity(ast2)}")
    print(f"Hashes match: {canonicalizer.compute_identity(ast1) == canonicalizer.compute_identity(ast2)}")
    
    # Merge
    merged = canonicalizer.merge(ast1, ast2)
    print(f"Merged AST nodes: {len(merged.nodes)}")
    
    print()


def demo_full_flow():
    """Demo: Complete flow from text to execution."""
    print("=" * 60)
    print("DEMO 6: Full Cosmos Flow")
    print("=" * 60)
    print()
    print("User Input: 'Create a report analyzing sales data'")
    print()
    
    # Step 1: Parse
    parser = CosmosParser()
    from solvens.cosmos.parser import InputFormat
    result = parser.parse("Create a report analyzing sales data", format=InputFormat.NATURAL)
    
    print("Step 1: Parse → AST")
    print(f"  Success: {result.success}")
    if result.ast:
        print(f"  AST created with {len(result.ast.nodes)} nodes")
    print()
    
    # Step 2: Canonicalize
    if result.ast:
        canonicalizer = CosmosCanonicalizer()
        canonical_ast = canonicalizer.canonicalize(result.ast)
        
        print("Step 2: Canonicalize → Canonical AST")
        print(f"  Canonical hash: {canonicalizer.compute_identity(canonical_ast)}")
        print()
    
    # Step 3: Plan
    print("Step 3: Plan → Execution Plan")
    dag = CosmosDAG()
    task_node = DAGNode(
        name="sales_report",
        node_type="task",
        operation="create_report",
        provider="anthropic"
    )
    dag.add_node(task_node)
    
    planner = CosmosPlanner()
    plan = planner.plan(dag)
    
    print(f"  Phases: {len(plan.phases)}")
    print(f"  Estimated cost: {plan.total_cost:.2f}")
    print()
    
    # Step 4: Execute (simulated)
    print("Step 4: Execute → Results")
    runtime = CosmosRuntime()
    print("  Runtime created and ready for execution")
    print()
    
    print("Flow: Text → AST → Canonical → DAG → Plan → Execute ✓")
    print()


def main():
    """Run all demos."""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "COSMOS INTEGRATION DEMO" + " " * 22 + "║")
    print("║" + " " * 10 + "SOLVENS CORE v0.1.0" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    demo_dsl_parsing()
    demo_dag_construction()
    demo_planning()
    demo_canonicalization()
    demo_full_flow()
    
    print("=" * 60)
    print("All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
