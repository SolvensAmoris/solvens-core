"""
solvens/cli/run.py
==================

Solvers CLI Run Command
======================

Ejecuta comandos y agentes.

Usage:
    solvens run "compile <file.cosmos>"
    solvens run "agent <agent_name> <task>"
    solvens run "cosmos <file.cosmos> --strict"

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

try:
    from solvens.cosmos.moat_parser import CosmosParser, CosmosDAG
    from cosmos.solvens_agent import CosmosCompilerAgent, Status, Message
except ImportError as e:
    print(f"Error importing: {e}")

app = typer.Typer(name="run", help="Run commands and agents")
console = Console()


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


def print_info(text: str):
    console.print(f"[blue]ℹ[/blue] {text}")


@app.command()
def main(
    command: str = typer.Argument(..., help="Command to run: 'compile <file>' or 'agent <name> <task>'"),
    strict: bool = typer.Option(False, "--strict", help="Strict mode validation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Run a Solvens command or agent.
    
    Examples:
        solvens run "compile myfile.cosmos"
        solvens run "compile myfile.cosmos --strict"
        solvens run "cosmos examples/research_agent.cosmos"
    """
    print_header("Solvens Run")
    
    # Parse command
    parts = command.split()
    if not parts:
        print_error("No command provided")
        raise typer.Exit(1)
    
    cmd = parts[0].lower()
    args = parts[1:]
    
    # Route command
    if cmd in ["compile", "cosmos"]:
        asyncio.run(run_compile(args, strict, verbose))
    elif cmd == "agent":
        asyncio.run(run_agent(args))
    else:
        print_error(f"Unknown command: {cmd}")
        console.print("Available commands:")
        console.print("  compile <file>  - Compile Cosmos file")
        console.print("  cosmos <file>   - Compile Cosmos file")
        console.print("  agent <name>   - Run named agent")
        raise typer.Exit(1)


async def run_compile(args: list, strict: bool, verbose: bool):
    """Run Cosmos compilation."""
    
    if not args:
        print_error("No file provided")
        console.print("Usage: solvens run \"compile <file.cosmos>\"")
        raise typer.Exit(1)
    
    file_path = Path(args[0])
    
    if not file_path.exists():
        # Try in examples/
        file_path = Path("examples") / args[0]
        if not file_path.exists():
            # Try in tests/
            file_path = Path("tests") / args[0]
            if not file_path.exists():
                print_error(f"File not found: {args[0]}")
                raise typer.Exit(1)
    
    print_info(f"Compiling: {file_path}")
    
    # Read file
    try:
        source = file_path.read_text()
    except Exception as e:
        print_error(f"Failed to read file: {e}")
        raise typer.Exit(1)
    
    # Create agent
    agent = CosmosCompilerAgent(strict_mode=strict, fail_fast=True)
    
    # Run compilation
    console.print(f"\n[dim]Strict mode: {strict}[/dim]")
    console.print("[yellow]Compiling...[/yellow]\n")
    
    result = await agent.run(source)
    
    # Output result
    if result.status == Status.APPROVED:
        print_success(f"Compilation successful!")
        console.print(f"\n[bold]DAG Summary:[/bold]")
        console.print(f"  Nodes: {result.metadata.get('nodes', 0)}")
        console.print(f"  Layers: {result.metadata.get('layers', 0)}")
        
        if verbose and 'dag' in result.metadata:
            import json
            console.print("\n[bold]DAG:[/bold]")
            console.print(f"[dim]{json.dumps(result.metadata['dag'], indent=2)[:500]}...[/dim]")
        
    elif result.status == Status.REJECTED:
        print_error(f"Compilation rejected!")
        console.print(f"\n[bold red]Error:[/bold red]")
        console.print(f"  Code: {result.metadata.get('error_code', 'UNKNOWN')}")
        console.print(f"  Message: {result.content}")
        
        if 'details' in result.metadata:
            console.print(f"\n[bold]Details:[/bold]")
            for k, v in result.metadata['details'].items():
                console.print(f"  {k}: {v}")
        
        # RFC-0004-F: Fail-fast
        if result.metadata.get('error_code') == 'TemporalConstraintViolation':
            console.print("\n[bold red]RFC-0004-F VIOLATION[/bold red]")
            console.print("[red]Fail-fast triggered. Compilation aborted.[/red]")
        
    elif result.status == Status.ERROR:
        print_error(f"Internal error!")
        console.print(f"  {result.content}")
    
    console.print()
    
    # Return exit code
    if result.status == Status.APPROVED:
        raise typer.Exit(0)
    else:
        raise typer.Exit(1)


async def run_agent(args: list):
    """Run named agent."""
    
    if len(args) < 2:
        print_error("Missing arguments")
        console.print("Usage: solvens run \"agent <name> <task>\"")
        raise typer.Exit(1)
    
    agent_name = args[0]
    task_input = " ".join(args[1:])
    
    print_info(f"Running agent: {agent_name}")
    
    # Load agent from entry points
    try:
        # Try to import from plugins
        from importlib.metadata import entry_points
        
        eps = entry_points(group="solvens.agents")
        agent_ep = None
        
        for ep in eps:
            if ep.name == agent_name:
                agent_ep = ep
                break
        
        if not agent_ep:
            print_error(f"Agent not found: {agent_name}")
            console.print("\n[bold]Available agents:[/bold]")
            for ep in eps:
                console.print(f"  - {ep.name}")
            raise typer.Exit(1)
        
        agent = agent_ep.load()()
        
        console.print(f"[dim]Agent loaded: {agent.name} v{agent.version if hasattr(agent, 'version') else '?'}[/dim]\n")
        
        # Run agent
        class SimpleTask:
            def __init__(self, name, input):
                self.name = name
                self.input = input
                self.metadata = {}
        
        task = SimpleTask(name=agent_name, input=task_input)
        result = await agent.run(task)
        
        # Output
        if result.status == Status.APPROVED:
            print_success("Agent completed successfully!")
        else:
            print_error(f"Agent failed: {result.status.value}")
        
        console.print(f"\n[bold]Output:[/bold]")
        console.print(result.content)
        
        if result.metadata:
            console.print(f"\n[bold]Metadata:[/bold]")
            for k, v in result.metadata.items():
                console.print(f"  {k}: {v}")
        
    except Exception as e:
        print_error(f"Failed to run agent: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
