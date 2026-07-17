#!/usr/bin/env python3
"""
solvens/cli/launch.py
=====================

SOLVENS LAUNCH CLI
==================

CLI killer para crear agentes auto-monetizados en 1 comando.

Usage:
    solvens launch revenue-agent
    solvens launch legal-agent
    solvens launch market-agent
    solvens status
    solvens battle grok-vs-claude

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
except ImportError:
    print("Installing dependencies...")
    os.system("pip install typer rich --quiet")
    import typer
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint

from solvens.runtime.orchestrator import RuntimeOrchestrator, TaskPriority
from solvens.router.smart_router import get_router, SmartRouter, ProviderType
from solvens.plugins.revenue.self_billing_agent import SelfBillingAgent, AgentConfig

app = typer.Typer(
    name="solvens",
    help="Solvens Core - AI Operating System Kernel",
    add_completion=False
)

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


def print_info(text: str):
    console.print(f"[blue]ℹ[/blue] {text}")


# ============================================================
# COMMANDS
# ============================================================

@app.command()
def launch(
    agent_type: str = typer.Argument(..., help="Agent type: revenue, legal, market, battle"),
    name: str = typer.Option("agent-1", "--name", "-n", help="Agent name"),
    price: float = typer.Option(25.0, "--price", "-p", help="Base price per job"),
    trust_mode: bool = typer.Option(False, "--trust", help="Skip payment verification"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """
    Launch a self-monetizing agent.
    
    Examples:
        solvens launch revenue --name my-agent --price 50
        solvens launch legal --trust
        solvens launch market
    """
    print_header("Solvens Launch")
    
    # Validate agent type
    valid_types = ["revenue", "legal", "market", "battle"]
    if agent_type not in valid_types:
        print_error(f"Invalid agent type: {agent_type}")
        console.print(f"Valid types: {', '.join(valid_types)}")
        raise typer.Exit(1)
    
    console.print(f"\n[cyan]Initializing {agent_type} agent...[/cyan]")
    
    # Create agent config
    config = AgentConfig(
        name=name or f"{agent_type}-agent",
        base_price=price,
        min_balance=10.0
    )
    
    # Initialize agent
    agent = SelfBillingAgent(config)
    
    print_success(f"Agent '{config.name}' created")
    print_info(f"Base price: ${config.base_price}")
    print_info(f"Trust mode: {'Enabled' if trust_mode else 'Disabled'}")
    
    # Demo: Create and execute a job
    console.print("\n[cyan]Starting agent loop...[/cyan]")
    
    async def agent_loop():
        job_count = 0
        while True:
            # Simulate receiving jobs
            await asyncio.sleep(3)
            
            # Create job
            job_prompts = [
                f"Generate report for {agent_type} task",
                f"Process {agent_type} request",
                f"Analyze market data for {agent_type}",
            ]
            
            prompt = job_prompts[job_count % len(job_prompts)]
            job = await agent.create_job(prompt, trust_mode=trust_mode)
            
            console.print(f"\n[yellow]New job:[/yellow] {job.id}")
            console.print(f"[dim]Prompt: {prompt}[/dim]")
            
            # Execute
            async def mock_execute():
                await asyncio.sleep(1)
                router = get_router()
                result = await router.execute(f"Execute: {prompt}")
                return result.get("content", "Completed")
            
            job = await agent.execute_job(job, mock_execute)
            
            if job.status == "completed":
                print_success(f"Job completed: ${job.price} - ${job.cost} = ${job.profit}")
            else:
                print_error(f"Job failed: {job.result}")
            
            job_count += 1
    
    try:
        asyncio.run(agent_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Agent stopped[/yellow]")
        
        # Show final report
        console.print("\n" + agent.generate_report())


@app.command()
def status():
    """
    Show system status.
    """
    print_header("Solvens Status")
    
    # Runtime status
    console.print("\n[bold]Runtime[/bold]")
    runtime = RuntimeOrchestrator()
    stats = runtime.get_stats()
    
    table = Table(show_header=True)
    table.add_column("Metric")
    table.add_column("Value")
    
    for k, v in stats.items():
        table.add_row(k, str(v))
    
    console.print(table)
    
    # Router status
    console.print("\n[bold]Router[/bold]")
    router = get_router()
    router_stats = router.get_stats()
    
    for provider, pstats in router_stats.get("providers", {}).items():
        available = "🟢" if pstats.get("available") else "🔴"
        console.print(f"{available} {provider}: {pstats.get('requests', 0)} requests")


@app.command()
def battle(
    left: str = typer.Argument(..., help="Left provider (grok, claude, gpt)"),
    right: str = typer.Argument(..., help="Right provider (grok, claude, gpt)"),
    prompt: str = typer.Option(
        "Explain why AI will change the legal industry in 2025",
        "--prompt", "-p",
        help="Battle prompt"
    ),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of rounds"),
):
    """
    Battle: Compare two AI providers.
    
    Examples:
        solvens battle grok claude --prompt "Write a poem"
        solvens battle gpt gemini --rounds 5
    """
    print_header(f"Battle: {left} vs {right}")
    
    console.print(f"\n[cyan]Prompt:[/cyan] {prompt}")
    console.print(f"[cyan]Rounds:[/cyan] {rounds}")
    
    router = get_router()
    
    providers_map = {
        "grok": ProviderType.GROK,
        "claude": ProviderType.ANTHROPIC,
        "gpt": ProviderType.OPENAI,
        "gemini": ProviderType.GOOGLE,
    }
    
    left_provider = providers_map.get(left.lower())
    right_provider = providers_map.get(right.lower())
    
    if not left_provider:
        print_error(f"Unknown provider: {left}")
        return
    if not right_provider:
        print_error(f"Unknown provider: {right}")
        return
    
    async def run_battle():
        scores = {left: 0, right: 0}
        
        for round_num in range(1, rounds + 1):
            console.print(f"\n[bold]Round {round_num}/{rounds}[/bold]")
            
            # Left
            console.print(f"\n[yellow]{left.upper()}:[/yellow]")
            try:
                routing = await router.route(prompt, preferred_provider=left_provider)
                result = await router.execute(prompt, preferred_provider=left_provider)
                response_left = result.get("content", "No response")
                console.print(f"[dim]{response_left[:200]}...[/dim]")
                scores[left] += 1
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
            
            await asyncio.sleep(0.5)
            
            # Right
            console.print(f"\n[yellow]{right.upper()}:[/yellow]")
            try:
                routing = await router.route(prompt, preferred_provider=right_provider)
                result = await router.execute(prompt, preferred_provider=right_provider)
                response_right = result.get("content", "No response")
                console.print(f"[dim]{response_right[:200]}...[/dim]")
                scores[right] += 1
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        # Winner
        console.print("\n" + "=" * 60)
        if scores[left] > scores[right]:
            console.print(f"[bold green]WINNER: {left.upper()}![/bold green]")
        elif scores[right] > scores[left]:
            console.print(f"[bold green]WINNER: {right.upper()}![/bold green]")
        else:
            console.print(f"[bold yellow]TIE![/bold yellow]")
        console.print("=" * 60)
    
    asyncio.run(run_battle())


@app.command()
def router_test():
    """
    Test the smart router.
    """
    print_header("Router Test")
    
    router = get_router()
    
    test_prompts = [
        ("Write Python code", "code"),
        ("Research AI regulations", "research"),
        ("Analyze this contract", "legal"),
    ]
    
    async def run_tests():
        for prompt, expected in test_prompts:
            console.print(f"\n[cyan]Prompt:[/cyan] {prompt}")
            console.print(f"[dim]Expected: {expected}[/dim]")
            
            result = await router.route(prompt)
            console.print(f"[green]→ {result.provider.value}: {result.reason}[/green]")
    
    asyncio.run(run_tests())


@app.command()
def init(
    path: str = typer.Option(".", "--path", help="Project path"),
):
    """
    Initialize Solvens in a project.
    """
    project_path = Path(path)
    
    console.print(f"\n[cyan]Initializing Solvens at {project_path}...[/cyan]")
    
    # Create directories
    dirs = [".solvens", ".solvens/plugins", ".solvens/workflows"]
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
    
    # Create config
    config = """# Solvens Configuration
[agent]
name = "my-agent"
base_price = 25.0

[providers]
grok = { enabled = true }
ollama = { enabled = true }

[limits]
max_concurrent = 5
"""
    
    (project_path / ".solvens" / "config.toml").write_text(config)
    
    print_success("Solvens initialized")
    print_info("Config: .solvens/config.toml")


# ============================================================
# MAIN
# ============================================================

def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
