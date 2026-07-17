"""CLI interface for SOLVENS CORE.

Usage:
    solvens chat
    solvens doctor
    solvens providers
    solvens models
    solvens plugins
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from solvens import __version__
from solvens.agents.orchestrator import AgentOrchestrator
from solvens.core.config import get_settings
from solvens.core.types import ProviderType
from solvens.plugins.openai import OpenAIClient
from solvens.plugins.anthropic import AnthropicClient
from solvens.plugins.ollama import OllamaClient
from solvens.registry.manager import PluginManager
from solvens.router import CapabilityRouter

app = typer.Typer(
    name="solvens",
    help="SOLVENS CORE - AI Operating System",
    add_completion=False,
)

console = Console()
settings = get_settings()


@app.command()
def version():
    """Show version information."""
    console.print(f"[bold]SOLVENS CORE[/bold] v{__version__}")
    console.print(f"Author: Luis Alberto Burciaga Miker")
    console.print(f"Organization: Solvens Amoris")


@app.command()
def doctor():
    """Check system health and configuration."""
    console.print("[bold]SOLVENS CORE - Health Check[/bold]\n")
    
    # Check Python version
    py_version = sys.version
    console.print(f"[green]✓[/green] Python: {py_version.split()[0]}")
    
    # Check configuration
    console.print(f"\n[bold]Configuration:[/bold]")
    console.print(f"  App: {settings.app_name}")
    console.print(f"  Debug: {settings.debug}")
    console.print(f"  Log Level: {settings.log_level}")
    console.print(f"  Data Dir: {settings.data_dir}")
    
    # Check providers
    console.print(f"\n[bold]Provider Configuration:[/bold]")
    providers_status = []
    
    if settings.openai_api_key:
        providers_status.append(("OpenAI", True, "API key configured"))
    else:
        providers_status.append(("OpenAI", False, "No API key"))
    
    if settings.anthropic_api_key:
        providers_status.append(("Anthropic", True, "API key configured"))
    else:
        providers_status.append(("Anthropic", False, "No API key"))
    
    for name, configured, status in providers_status:
        icon = "[green]✓[/green]" if configured else "[red]✗[/red]"
        console.print(f"  {icon} {name}: {status}")
    
    # Check Ollama (local)
    try:
        ollama = OllamaClient()
        console.print(f"  [yellow]?[/yellow] Ollama: Not checked (run 'solvens providers --check')")
    except Exception as e:
        console.print(f"  [red]✗[/red] Ollama: {e}")
    
    console.print("\n[bold]System Status:[/bold] ✓ Healthy")


@app.command()
def providers(
    check: bool = typer.Option(False, "--check", help="Check provider health"),
):
    """List and manage providers."""
    console.print("[bold]Available Providers[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Models")
    
    providers = [
        ("OpenAI", ProviderType.OPENAI.value, "configured" if settings.openai_api_key else "no key", "gpt-4, gpt-3.5"),
        ("Anthropic", ProviderType.ANTHROPIC.value, "configured" if settings.anthropic_api_key else "no key", "claude-3.5-sonnet"),
        ("Ollama", ProviderType.OLLAMA.value, "local", "llama3.2, codellama"),
        ("Google", ProviderType.GOOGLE.value, "configured" if settings.google_api_key else "no key", "gemini-pro"),
        ("DeepSeek", ProviderType.DEEPSEEK.value, "configured" if settings.deepseek_api_key else "no key", "deepseek-chat"),
    ]
    
    for name, ptype, status, models in providers:
        table.add_row(name, ptype, status, models)
    
    console.print(table)
    
    if check:
        console.print("\n[bold]Checking Provider Health...[/bold]")
        # Would check actual provider connectivity here
        console.print("[yellow]Note: Full health checks require API keys[/yellow]")


@app.command()
def models(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider"),
):
    """List available models."""
    console.print("[bold]Available Models[/bold]\n")
    
    all_models = [
        ("OpenAI", "gpt-4-turbo", "GPT-4 Turbo", "chat, function_calling, streaming"),
        ("OpenAI", "gpt-4", "GPT-4", "chat, function_calling, streaming"),
        ("OpenAI", "gpt-3.5-turbo", "GPT-3.5 Turbo", "chat, function_calling, streaming"),
        ("OpenAI", "text-embedding-3-small", "Embedding 3 Small", "embeddings"),
        ("Anthropic", "claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", "chat, vision, streaming"),
        ("Anthropic", "claude-3-5-haiku-20241022", "Claude 3.5 Haiku", "chat, vision, streaming"),
        ("Anthropic", "claude-3-opus-20240229", "Claude 3 Opus", "chat, vision, streaming"),
        ("Ollama", "llama3.2", "Llama 3.2", "chat, streaming"),
        ("Ollama", "llama3.2-vision", "Llama 3.2 Vision", "chat, vision, streaming"),
        ("Ollama", "codellama", "Code Llama", "chat, streaming"),
        ("Ollama", "nomic-embed-text", "Nomic Embed Text", "embeddings"),
    ]
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider")
    table.add_column("Model ID")
    table.add_column("Name")
    table.add_column("Capabilities")
    
    for p, mid, name, caps in all_models:
        if provider is None or p.lower() == provider.lower():
            table.add_row(p, mid, name, caps)
    
    console.print(table)


@app.command()
def plugins():
    """List loaded plugins."""
    console.print("[bold]Plugin System[/bold]\n")
    
    manager = PluginManager()
    
    console.print(f"Plugins Directory: {manager.plugins_dir}")
    console.print(f"Registered: {len(manager.list_plugins())}")
    console.print(f"Loaded: {len(manager.list_loaded_plugins())}")
    
    console.print("\n[bold]Built-in Provider Plugins:[/bold]")
    builtins = [
        ("openai", "OpenAI GPT models"),
        ("anthropic", "Anthropic Claude models"),
        ("ollama", "Local LLM inference"),
    ]
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Plugin")
    table.add_column("Description")
    
    for name, desc in builtins:
        table.add_row(name, desc)
    
    console.print(table)


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message to send"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Provider to use"),
):
    """Send a chat message."""
    console.print(f"[dim]Sending message...[/dim]")
    
    # This would integrate with the orchestrator and router
    console.print(f"\n[bold]Note:[/bold] Full chat requires API keys and running API server")
    console.print(f"Start with: uvicorn solvens.api.main:app")


@app.command()
def info():
    """Show detailed system information."""
    console.print("[bold]SOLVENS CORE - System Information[/bold]\n")
    
    console.print(f"Version: {__version__}")
    console.print(f"Author: Luis Alberto Burciaga Miker")
    console.print(f"Organization: Solvens Amoris")
    console.print(f"Repository: github.com/SolvensAmoris/solvens-core\n")
    
    console.print("[bold]Architecture:[/bold]")
    console.print("  - Agent Orchestrator")
    console.print("  - Capability Router")
    console.print("  - Provider System")
    console.print("  - Plugin Registry")
    console.print("  - REST API")
    console.print("  - CLI Interface")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
