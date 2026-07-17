"""
solvens/cli/plugins.py
=====================

Solvers CLI Plugins Command
===========================

Lista y gestiona plugins de Solvens.

Usage:
    solvens plugins list
    solvens plugins install <name>
    solvens plugins info <name>

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app = typer.Typer(name="plugins", help="Manage Solvens plugins")
console = Console()


def print_header(text: str):
    """Print stylized header."""
    from rich.panel import Panel
    console.print(Panel(
        f"[bold cyan]{text}[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))


@app.command()
def list(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    filter: str = typer.Option(None, "--filter", "-f", help="Filter by name"),
):
    """
    List all available Solvens plugins.
    
    Examples:
        solvens plugins list
        solvens plugins list --filter cosmos
        solvens plugins list -v
    """
    print_header("Solvens Plugins")
    
    # Load entry points
    plugins = []
    
    try:
        from importlib.metadata import entry_points
        
        # Get solvens agents
        try:
            eps = entry_points(group="solvens.agents")
            for ep in eps:
                if not filter or filter.lower() in ep.name.lower():
                    plugins.append({
                        "name": ep.name,
                        "type": "agent",
                        "module": ep.module,
                        "object": ep.object,
                    })
        except Exception:
            pass
        
        # Get solvens providers
        try:
            eps = entry_points(group="solvens.providers")
            for ep in eps:
                if not filter or filter.lower() in ep.name.lower():
                    plugins.append({
                        "name": ep.name,
                        "type": "provider",
                        "module": ep.module,
                        "object": ep.object,
                    })
        except Exception:
            pass
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load plugins: {e}[/yellow]")
        console.print("[dim]Install plugins with: pip install solvens-plugins[/dim]")
        plugins = []
    
    # Add built-in plugins
    builtins = [
        {"name": "cosmos", "type": "agent", "module": "cosmos.solvens_agent", "description": "Cosmos DSL compiler and validator"},
        {"name": "runtime", "type": "runtime", "module": "solvens.runtime.orchestrator", "description": "Task orchestrator"},
        {"name": "router", "type": "router", "module": "solvens.router.smart_router", "description": "Smart task router"},
        {"name": "hybrid-kg", "type": "memory", "module": "solvens.memory.hybrid_kg", "description": "Hybrid knowledge graph"},
    ]
    
    for b in builtins:
        if not filter or filter.lower() in b["name"].lower():
            plugins.append(b)
    
    if not plugins:
        console.print("[yellow]No plugins found.[/yellow]")
        return
    
    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Module", style="dim")
    
    if verbose:
        table.add_column("Description", style="white")
    
    for plugin in plugins:
        row = [
            plugin["name"],
            plugin["type"],
            plugin["module"],
        ]
        if verbose:
            row.append(plugin.get("description", ""))
        table.add_row(*row)
    
    console.print(table)
    console.print(f"\n[dim]Total plugins: {len(plugins)}[/dim]")
    
    if verbose:
        console.print("\n[bold]Usage:[/bold]")
        console.print("  solvens run \"compile myfile.cosmos\"  # Use cosmos plugin")
        console.print("  solvens plugins info <name>           # Get plugin info")


@app.command()
def info(
    name: str = typer.Argument(..., help="Plugin name"),
):
    """
    Show detailed information about a plugin.
    
    Examples:
        solvens plugins info cosmos
        solvens plugins info router
    """
    print_header(f"Plugin: {name}")
    
    # Built-in plugins info
    plugins_info = {
        "cosmos": {
            "name": "cosmos",
            "type": "agent",
            "version": "0.4.5-rc1",
            "module": "cosmos.solvens_agent:CosmosCompilerAgent",
            "description": "Cosmos DSL compiler and validator with RFC-0004-F support",
            "features": [
                "Syntax validation",
                "Semantic validation", 
                "Temporal constraint validation",
                "Fail-fast error handling",
                "DAG compilation",
            ],
            "rfc": "RFC-0004-F: Temporal Constraint Validation",
        },
        "runtime": {
            "name": "runtime",
            "type": "runtime",
            "version": "0.2.0",
            "module": "solvens.runtime.orchestrator:RuntimeOrchestrator",
            "description": "Ultra-light task orchestrator with priority queue",
            "features": [
                "Priority queue",
                "Async execution",
                "Plugin hooks",
                "Metrics",
            ],
        },
        "router": {
            "name": "router",
            "type": "router",
            "version": "0.2.0",
            "module": "solvens.router.smart_router:SmartRouter",
            "description": "Intelligent task router with multi-provider support",
            "features": [
                "Task type detection",
                "Cost-based routing",
                "Provider fallbacks",
                "Grok + Ollama",
            ],
        },
        "hybrid-kg": {
            "name": "hybrid-kg",
            "type": "memory",
            "version": "0.4.0",
            "module": "solvens.memory.hybrid_kg:HybridKnowledgeGraph",
            "description": "Hybrid knowledge graph with vector + graph storage",
            "features": [
                "ChromaDB vector store",
                "NetworkX graph",
                "Sentence transformers",
                "Louvain clustering",
                "Node embeddings",
            ],
        },
    }
    
    info = plugins_info.get(name.lower())
    
    if not info:
        console.print(f"[yellow]Plugin '{name}' not found.[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Name:[/bold cyan] {info['name']}")
    console.print(f"[bold cyan]Type:[/bold cyan] {info['type']}")
    console.print(f"[bold cyan]Version:[/bold cyan] {info.get('version', 'unknown')}")
    console.print(f"[bold cyan]Module:[/bold cyan] {info['module']}")
    console.print(f"\n[bold]Description:[/bold]")
    console.print(f"  {info['description']}")
    
    if 'features' in info:
        console.print(f"\n[bold]Features:[/bold]")
        for feature in info['features']:
            console.print(f"  [green]✓[/green] {feature}")
    
    if 'rfc' in info:
        console.print(f"\n[bold yellow]RFC:[/bold yellow] {info['rfc']}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
):
    """
    Search for plugins by keyword.
    
    Examples:
        solvens plugins search cosmos
        solvens plugins search dag
    """
    print_header(f"Search: {query}")
    
    # Search in built-in plugins
    all_plugins = [
        {"name": "cosmos", "description": "Cosmos DSL compiler and validator"},
        {"name": "runtime", "description": "Task orchestrator"},
        {"name": "router", "description": "Smart task router"},
        {"name": "hybrid-kg", "description": "Hybrid knowledge graph"},
        {"name": "cosmos-visualizer", "description": "Cosmos DAG visualizer"},
        {"name": "cosmos-executor", "description": "Cosmos DAG executor"},
        {"name": "self-billing", "description": "Self-billing agent"},
    ]
    
    results = []
    query_lower = query.lower()
    
    for plugin in all_plugins:
        if (query_lower in plugin["name"].lower() or 
            query_lower in plugin["description"].lower()):
            results.append(plugin)
    
    if not results:
        console.print(f"[yellow]No plugins found for '{query}'.[/yellow]")
        return
    
    console.print(f"[green]Found {len(results)} plugins:[/green]\n")
    
    for plugin in results:
        console.print(f"[cyan]{plugin['name']}[/cyan]")
        console.print(f"  {plugin['description']}\n")


if __name__ == "__main__":
    app()
