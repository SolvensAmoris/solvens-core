#!/usr/bin/env python3
"""
solvens/cli/cosmos.py
====================

COSMOS CLI - Visualize and Execute Cosmos DAGs

Commands:
    solvens cosmos parse <file.cosmos>
    solvens cosmos visualize <file.cosmos>
    solvens cosmos execute <file.cosmos>
    solvens cosmos optimize <file.cosmos>

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich import print as rprint

try:
    from solvens.cosmos.moat_parser import CosmosParser, CosmosDAG
    from solvens.cosmos.moat_executor import CosmosExecutor
    from solvens.router.smart_router import get_router
except ImportError as e:
    print(f"Error importing: {e}")
    print("Run from project root or install dependencies")
    sys.exit(1)

app = typer.Typer(name="cosmos", help="Cosmos DAG commands")
console = Console()


# ============================================================
# HELPERS
# ============================================================

def print_header(text: str):
    """Print stylized header."""
    console.print(Panel(
        f"[bold cyan]{text}[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))


def print_success(text: str):
    console.print(f"[green]✓[/green] {text}")


def print_error(text: str):
    console.print(f"[red]✗[/red] {text}")


# ============================================================
# COMMANDS
# ============================================================

@app.command()
def parse(
    file: Path = typer.Argument(..., help="Cosmos file to parse"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON file"),
):
    """
    Parse a Cosmos file and show structure.
    """
    print_header(f"Parsing: {file}")
    
    if not file.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)
    
    cosmos_code = file.read_text()
    
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    
    console.print("\n[bold]Universe:[/bold]", dag.universe)
    console.print(f"[dim]Hash: {dag.graph_hash[:32]}[/dim]")
    console.print(f"[dim]Nodes: {len(dag.nodes)}, Edges: {len(dag.edges)}[/dim]")
    console.print(f"[dim]Layers: {len(dag.layers)}[/dim]")
    
    # Show tree
    tree = Tree(f"🌌 {dag.universe}")
    
    for layer_idx, layer in enumerate(dag.layers):
        layer_tree = tree.add(f"[blue]Layer {layer_idx + 1}[/blue]")
        
        for node_id in layer:
            if node_id in dag.nodes:
                node = dag.nodes[node_id]
                icon = {
                    "sun": "☀️",
                    "planet": "🪐",
                    "galaxy": "🌌",
                    "light": "💡",
                    "star": "⭐",
                }.get(node.node_type.value, "●")
                
                props = ", ".join(f"{k}={v}" for k, v in list(node.properties.items())[:2])
                layer_tree.add(f"{icon} {node.name} [dim]({props})[/dim]")
    
    console.print("\n")
    console.print(tree)
    
    # Save JSON if requested
    if output:
        output.write_text(json.dumps(dag.to_dict(), indent=2, default=str))
        print_success(f"Saved to: {output}")


@app.command()
def visualize(
    file: Path = typer.Argument(..., help="Cosmos file to visualize"),
    format: str = typer.Option("ascii", "--format", "-f", help="Output format: ascii, svg, html"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Visualize a Cosmos DAG.
    """
    print_header(f"Visualizing: {file}")
    
    cosmos_code = file.read_text()
    
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    
    if format == "ascii":
        console.print("\n" + dag.visualize_text())
    
    elif format == "json":
        console.print(json.dumps(dag.to_dict(), indent=2, default=str))
    
    else:
        print_error(f"Unknown format: {format}")
        raise typer.Exit(1)
    
    if output:
        output.write_text(dag.visualize_text())
        print_success(f"Saved to: {output}")


@app.command()
def execute(
    file: Path = typer.Argument(..., help="Cosmos file to execute"),
    input_data: str = typer.Option("{}", "--input", "-i", help="Input data as JSON string"),
    consensus: bool = typer.Option(False, "--consensus", help="Enable multi-provider consensus"),
):
    """
    Execute a Cosmos DAG.
    """
    print_header(f"Executing: {file}")
    
    cosmos_code = file.read_text()
    
    # Parse
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    console.print(f"\n[dim]Parsed: {len(dag.nodes)} nodes, {len(dag.edges)} edges[/dim]")
    console.print(dag.visualize_text())
    
    # Load input
    try:
        input_dict = json.loads(input_data)
    except:
        input_dict = {"query": input_data}
    
    # Execute
    console.print("\n[yellow]Executing...[/yellow]")
    
    router = get_router()
    executor = CosmosExecutor(router, enable_consensus=consensus)
    
    async def run():
        return await executor.execute(dag, input_dict)
    
    results = asyncio.run(run())
    
    # Show results
    console.print("\n[bold]Results:[/bold]")
    
    for node_id, result in results.items():
        status_color = {
            "success": "green",
            "failed": "red",
            "skipped": "yellow",
        }.get(result.status, "white")
        
        console.print(f"\n[{status_color}]{result.status.upper()}[/{status_color}] {node_id}")
        
        if result.output:
            resp = result.output.get("response", str(result.output))
            if isinstance(resp, str) and len(resp) > 100:
                resp = resp[:100] + "..."
            console.print(f"  [dim]{resp}[/dim]")
        
        if result.error:
            console.print(f"  [red]Error: {result.error}[/red]")
        
        console.print(f"  [dim]{result.duration_ms:.0f}ms[/dim]")
    
    # Stats
    stats = executor.get_stats()
    console.print("\n[bold]Execution Stats:[/bold]")
    console.print(f"  Duration: {stats.total_duration_ms:.0f}ms")
    console.print(f"  Success rate: {stats.success_rate:.1f}%")
    console.print(f"  Parallelization: {stats.parallelization_factor:.1f}x")
    console.print(f"  Total cost: ${stats.total_cost:.4f}")
    console.print(f"  Total tokens: {stats.total_tokens}")


@app.command()
def optimize(
    file: Path = typer.Argument(..., help="Cosmos file to optimize"),
):
    """
    Optimize a Cosmos DAG for better execution.
    """
    print_header(f"Optimizing: {file}")
    
    cosmos_code = file.read_text()
    
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    
    console.print(f"\n[dim]Before optimization:[/dim]")
    console.print(f"  Nodes: {len(dag.nodes)}")
    console.print(f"  Layers: {len(dag.layers)}")
    console.print(f"  Parallelization: {len(dag.nodes) / max(len(dag.layers), 1):.1f}x")
    
    # Optimize
    executor = CosmosExecutor()
    optimized = executor.optimize_dag(dag)
    
    console.print(f"\n[green]After optimization:[/green]")
    console.print(f"  Nodes: {len(optimized.nodes)}")
    console.print(f"  Layers: {len(optimized.layers)}")
    console.print(f"  Parallelization: {len(optimized.nodes) / max(len(optimized.layers), 1):.1f}x")
    console.print(f"  Hash: {optimized.graph_hash[:32]}")
    
    console.print("\n[bold]Optimized DAG:[/bold]")
    console.print(optimized.visualize_text())


@app.command()
def benchmark(
    file: Path = typer.Argument(..., help="Cosmos file to benchmark"),
    runs: int = typer.Option(5, "--runs", "-n", help="Number of runs"),
):
    """
    Benchmark Cosmos DAG execution.
    """
    print_header(f"Benchmarking: {file}")
    console.print(f"\n[dim]Running {runs} iterations...[/dim]\n")
    
    cosmos_code = file.read_text()
    
    parser = CosmosParser()
    dag = parser.parse(cosmos_code)
    
    router = get_router()
    executor = CosmosExecutor(router)
    
    times = []
    
    async def run():
        start = asyncio.get_event_loop().time()
        await executor.execute(dag, {"benchmark": True})
        return (asyncio.get_event_loop().time() - start) * 1000
    
    for i in range(runs):
        duration = asyncio.run(run())
        times.append(duration)
        console.print(f"  Run {i + 1}: {duration:.0f}ms")
    
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Average: {avg:.0f}ms")
    console.print(f"  Min: {min_time:.0f}ms")
    console.print(f"  Max: {max_time:.0f}ms")
    console.print(f"  Total: {sum(times):.0f}ms")
    
    # Estimate vs sequential
    sequential_est = sum(
        len(layer) * 100  # Assume 100ms per node
        for layer in dag.layers
    )
    speedup = sequential_est / avg if avg > 0 else 0
    
    console.print(f"\n[green]Speedup vs sequential: {speedup:.1f}x[/green]")


# ============================================================
# EXAMPLE FILES
# ============================================================

@app.command()
def example(
    name: str = typer.Argument("research", help="Example name: research, legal, market"),
):
    """
    Show an example Cosmos file.
    """
    examples = {
        "research": """
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
}
end
""",
        "legal": """
cosmos LegalAgent {
    sun LegalOrchestrator
    
    planet DocumentParser {
        model: claude-3-sonnet
    }
    
    planet LegalResearcher {
        model: claude-3-opus
    }
    
    planet OpinionWriter {
        model: gpt-4
    }
    
    light Flow {
        from: LegalOrchestrator
        to: [DocumentParser, LegalResearcher]
    }
}
end
""",
        "market": """
cosmos MarketAgent {
    sun MarketOrchestrator
    
    planet DataFetcher {
        model: gemini
    }
    
    planet Analyst {
        model: claude-3-sonnet
    }
    
    planet Reporter {
        model: gpt-4
    }
}
end
""",
    }
    
    example_code = examples.get(name, examples["research"])
    
    console.print(Panel(
        f"[bold cyan]Example: {name}[/bold cyan]\n\n[dim]{example_code}[/dim]",
        title="Cosmos Example",
        border_style="cyan"
    ))


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app()
