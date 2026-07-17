"""
SOLVENS CLI

Command-line interface for SOLVENS SDK.

Usage:
    solvens init my-project
    solvens run workflow.cosmos
    solvens simulate workflow.cosmos
    solvens deploy workflow.cosmos
    solvens publish
"""

import sys
import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from solvens import __version__
from solvens.compiler import load_cosmos_file, CosmosSyntaxError
from solvens.core import Cosmos

console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """SOLVENS - AI Agent Orchestration Platform"""
    pass


@cli.command()
@click.argument("name")
@click.option("--template", "-t", default="basic", help="Project template")
def init(name: str, template: str):
    """Initialize a new SOLVENS project."""
    
    project_dir = Path(name)
    
    if project_dir.exists():
        console.print(f"[red]Error:[/red] Directory '{name}' already exists")
        sys.exit(1)
    
    project_dir.mkdir(parents=True)
    
    # Create project structure
    (project_dir / "workflows").mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    
    # Create main workflow
    main_workflow = project_dir / "workflows" / "main.cosmos"
    main_workflow.write_text('''# Main workflow
# Edit this file to define your DAG

provider openai {
  type: "openai"
  model: "gpt-4o"
}

agent assistant {
  provider: openai
  system: "You are a helpful AI assistant"
}

task greet {
  agent: assistant
  description: "Generate a greeting"
}
''')
    
    # Create config
    config = project_dir / "solvens.json"
    config.write_text(json.dumps({
        "name": name,
        "version": "1.0.0",
        "api_url": "http://localhost:8000"
    }, indent=2))
    
    # Create README
    readme = project_dir / "README.md"
    readme.write_text(f'''# {name}

A SOLVENS AI Agent workflow project.

## Quick Start

```bash
cd {name}
solvens run workflows/main.cosmos
```

## Project Structure

```
{name}/
├── workflows/        # .cosmos workflow files
│   └── main.cosmos
├── src/             # Python/TS source files
├── tests/           # Test files
└── solvens.json     # Project config
```

## Commands

- `solvens run workflows/main.cosmos` - Execute workflow
- `solvens simulate workflows/main.cosmos` - Simulate without execution
- `solvens deploy workflows/main.cosmos` - Deploy as API endpoint
''')
    
    console.print(f"[green]✓[/green] Created project '{name}'")
    console.print(f"\nNext steps:")
    console.print(f"  cd {name}")
    console.print(f"  solvens run workflows/main.cosmos")


@cli.command()
@click.argument("workflow_file")
@click.option("--input", "-i", help="Input JSON for workflow")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--dashboard", is_flag=True, help="Open dashboard after starting")
def run(workflow_file: str, input: str, json_output: bool, dashboard: bool):
    """Run a workflow file."""
    
    path = Path(workflow_file)
    
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {workflow_file}")
        sys.exit(1)
    
    try:
        data = load_cosmos_file(path)
    except CosmosSyntaxError as e:
        console.print(f"[red]Syntax Error:[/red] {e}")
        sys.exit(1)
    
    console.print(f"[cyan]Running:[/cyan] {data.get('name', path.stem)}")
    console.print(f"[cyan]Tasks:[/cyan] {len(data.get('tasks', []))}")
    
    # Parse input if provided
    inputs = {}
    if input:
        try:
            inputs = json.loads(input)
        except json.JSONDecodeError:
            console.print(f"[red]Error:[/red] Invalid JSON in --input")
            sys.exit(1)
    
    # In real implementation, this would call the API
    # For now, just show what would be run
    console.print("\n[yellow]Note:[/yellow] Connect to API server to execute")
    console.print(f"  solvens run {workflow_file}")
    console.print("\nWorkflow summary:")
    
    table = Table(show_header=True)
    table.add_column("Task")
    table.add_column("Agent")
    table.add_column("Dependencies")
    
    for task in data.get("tasks", []):
        deps = task.get("depends_on", [])
        deps_str = ", ".join(deps) if deps else "-"
        table.add_row(
            task.get("name", "?"),
            task.get("agent", "?"),
            deps_str
        )
    
    console.print(table)
    
    if json_output:
        console.print(json.dumps(data, indent=2))


@cli.command()
@click.argument("workflow_file")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def simulate(workflow_file: str, json_output: bool):
    """Simulate a workflow without executing."""
    
    path = Path(workflow_file)
    
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {workflow_file}")
        sys.exit(1)
    
    try:
        data = load_cosmos_file(path)
    except CosmosSyntaxError as e:
        console.print(f"[red]Syntax Error:[/red] {e}")
        sys.exit(1)
    
    tasks = data.get("tasks", [])
    total_tasks = len(tasks)
    
    # Estimate cost (rough)
    estimated_cost = total_tasks * 0.005
    estimated_time = total_tasks * 5000  # 5s per task
    
    # Count by provider
    providers = {}
    for task in tasks:
        agent_name = task.get("agent", "unknown")
        provider = data.get("agents", [{}])[0].get("provider", "openai")
        providers[provider] = providers.get(provider, 0) + 1
    
    console.print(f"[cyan]Simulation:[/cyan] {path.stem}")
    console.print(f"[cyan]Total Tasks:[/cyan] {total_tasks}")
    console.print(f"[cyan]Estimated Time:[/cyan] {estimated_time/1000:.1f}s")
    console.print(f"[cyan]Estimated Cost:[/cyan] ${estimated_cost:.4f}")
    console.print(f"[cyan]Providers:[/cyan]")
    
    for provider, count in providers.items():
        pct = count / total_tasks * 100
        console.print(f"  {provider}: {count} tasks ({pct:.0f}%)")
    
    if json_output:
        console.print(json.dumps({
            "workflow": path.stem,
            "total_tasks": total_tasks,
            "estimated_time_ms": estimated_time,
            "estimated_cost_usd": estimated_cost,
            "providers": providers,
        }, indent=2))


@cli.command()
@click.argument("workflow_file")
@click.option("--public", is_flag=True, help="Make endpoint public")
@click.option("--name", "-n", help="Custom endpoint name")
def deploy(workflow_file: str, public: bool, name: str):
    """Deploy a workflow as an API endpoint."""
    
    path = Path(workflow_file)
    
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {workflow_file}")
        sys.exit(1)
    
    endpoint_name = name or path.stem
    visibility = "public" if public else "private"
    
    console.print(f"[green]✓[/green] Would deploy: {endpoint_name}")
    console.print(f"[cyan]Visibility:[/cyan] {visibility}")
    console.print(f"\n[yellow]Note:[/yellow] Deploy to api.solvens.ai for production")
    console.print(f"  solvens deploy {workflow_file} --public")


@cli.command()
@click.argument("workflow_file")
def validate(workflow_file: str):
    """Validate a workflow file."""
    
    path = Path(workflow_file)
    
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {workflow_file}")
        sys.exit(1)
    
    try:
        data = load_cosmos_file(path)
        console.print(f"[green]✓[/green] Valid: {workflow_file}")
        console.print(f"  Tasks: {len(data.get('tasks', []))}")
        console.print(f"  Agents: {len(data.get('agents', []))}")
        console.print(f"  Providers: {len(data.get('providers', []))}")
    except CosmosSyntaxError as e:
        console.print(f"[red]✗[/red] Invalid: {workflow_file}")
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option("--list", "list_all", is_flag=True, help="List all workflows")
def hub(list_all: bool):
    """Interact with Cosmos Hub (npm for AI agents)."""
    
    console.print("[cyan]Cosmos Hub[/cyan]")
    console.print("  Browse at: hub.solvens.ai")
    console.print("\nCommands:")
    console.print("  solvens hub search <query>  - Search workflows")
    console.print("  solvens hub install <name>  - Install a workflow")
    console.print("  solvens hub publish         - Publish your workflow")
    
    if list_all:
        console.print("\n[yellow]Featured Workflows:[/yellow]")
        console.print("  @solvens/crm-generator")
        console.print("  @solvens/doc-writer")
        console.print("  @solvens/audit-flow")


def main():
    cli()


if __name__ == "__main__":
    main()
