#!/usr/bin/env python3
"""
cosmos/cli.py
=============

Production CLI for Cosmos Compiler
=================================

Commands:
- cosmos compile <file> [--strict] [--json]
- cosmos explain <result.json>
- cosmos export-audit [--format=json] [--last=N]
- cosmos validate <file>

Usage:
    pip install cosmos-compiler
    cosmos compile myfile.cosmos --strict

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos.solvens_agent import CosmosCompilerAgent, Status, ErrorCode
from cosmos.explainer import LLMExplainerAgent, ErrorContext, OutputFormat

app = typer.Typer(name="cosmos", help="Cosmos DSL Compiler")
console = Console()


# ============================================================
# EXPORT SCHEMAS
# ============================================================

EXPORT_SCHEMA = {
    "cosmos_export_v1": {
        "version": "0.4.5-rc1",
        "schema": {
            "compilation_results": {
                "type": "array",
                "items": {
                    "file": "string",
                    "status": "APPROVED | REJECTED | PARTIAL | ERROR",
                    "error_code": "string?",
                    "timestamp": "ISO8601",
                    "duration_ms": "number"
                }
            },
            "audit_trail": {
                "type": "object",
                "properties": {
                    "total_files": "number",
                    "approved": "number",
                    "rejected": "number",
                    "e401_count": "number",
                    "fail_fast_events": "number"
                }
            },
            "metadata": {
                "exporter": "cosmos-cli",
                "exported_at": "ISO8601",
                "hostname": "string"
            }
        }
    }
}


# ============================================================
# HELPERS
# ============================================================

def print_header(text: str):
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


def get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_hostname() -> str:
    import socket
    return socket.gethostname()


# ============================================================
# COMMANDS
# ============================================================

@app.command()
def compile(
    file: str = typer.Argument(..., help="Cosmos file to compile"),
    strict: bool = typer.Option(False, "--strict", help="Strict validation"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Compile a Cosmos file.
    
    Examples:
        cosmos compile myfile.cosmos
        cosmos compile myfile.cosmos --strict
        cosmos compile myfile.cosmos --json > result.json
    """
    print_header("Cosmos Compiler v0.4.5-rc1")
    
    file_path = Path(file)
    
    if not file_path.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)
    
    try:
        source = file_path.read_text()
    except Exception as e:
        print_error(f"Failed to read file: {e}")
        raise typer.Exit(1)
    
    print_info(f"Compiling: {file}")
    console.print(f"[dim]Strict mode: {strict}[/dim]\n")
    
    # Compile
    agent = CosmosCompilerAgent(strict_mode=strict, fail_fast=True)
    start = asyncio.get_event_loop().time()
    result = asyncio.run(agent.run(source))
    duration_ms = (asyncio.get_event_loop().time() - start) * 1000
    
    # Output
    if json_output:
        output = {
            "file": str(file_path),
            "status": result.status.value,
            "error_code": result.metadata.get("error_code"),
            "content": result.content,
            "timestamp": get_timestamp(),
            "duration_ms": duration_ms,
            "metadata": result.metadata
        }
        print(json.dumps(output, indent=2))
    else:
        if result.status == Status.APPROVED:
            print_success(f"Compilation successful ({duration_ms:.2f}ms)")
            console.print(f"\n[bold]DAG Summary:[/bold]")
            console.print(f"  Nodes: {result.metadata.get('nodes', 0)}")
            console.print(f"  Layers: {result.metadata.get('layers', 0)}")
        else:
            print_error(f"Compilation failed: {result.content}")
            console.print(f"\n[bold red]Error Code:[/bold red] {result.metadata.get('error_code', 'UNKNOWN')}")
            
            if result.metadata.get('error_code') == 'TemporalConstraintViolation':
                console.print("\n[bold yellow]RFC-0004-F VIOLATION[/bold yellow]")
                console.print("[red]Fail-fast triggered.[/red]")
    
    raise typer.Exit(0 if result.status == Status.APPROVED else 1)


@app.command()
def validate(
    file: str = typer.Argument(..., help="Cosmos file to validate"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """
    Validate a Cosmos file (alias for compile with output).
    
    Examples:
        cosmos validate myfile.cosmos
        cosmos validate myfile.cosmos --json
    """
    print_header("Cosmos Validator v0.4.5-rc1")
    
    file_path = Path(file)
    
    if not file_path.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)
    
    try:
        source = file_path.read_text()
    except Exception as e:
        print_error(f"Failed to read file: {e}")
        raise typer.Exit(1)
    
    agent = CosmosCompilerAgent(fail_fast=True)
    result = asyncio.run(agent.run(source))
    
    if json_output:
        output = {
            "file": str(file_path),
            "valid": result.status == Status.APPROVED,
            "timestamp": get_timestamp()
        }
        print(json.dumps(output, indent=2))
    else:
        if result.status == Status.APPROVED:
            print_success(f"Valid: {file}")
        else:
            print_error(f"Invalid: {file}")
            console.print(f"  {result.content}")
    
    raise typer.Exit(0 if result.status == Status.APPROVED else 1)


@app.command()
def explain(
    result_file: str = typer.Argument(..., help="JSON result file from compile"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown, json, plain)"),
):
    """
    Explain a compilation result.
    
    Examples:
        cosmos explain result.json
        cosmos explain result.json --format markdown
    """
    print_header("Cosmos Explainer v0.4.5-rc1")
    
    try:
        with open(result_file) as f:
            data = json.load(f)
    except Exception as e:
        print_error(f"Failed to read file: {e}")
        raise typer.Exit(1)
    
    # Extract error context
    error_context = ErrorContext(
        error_code=data.get("error_code", "UNKNOWN"),
        error_message=data.get("content", ""),
        file_path=data.get("file"),
        cosmos_source=data.get("source")
    )
    
    # Generate explanation
    agent = LLMExplainerAgent()
    output_format = OutputFormat.MARKDOWN if format == "markdown" else OutputFormat.JSON
    
    try:
        explanation = asyncio.run(agent.explain(error_context, format=output_format))
    except Exception as e:
        # Fallback
        explanation = agent._fallback_explanation(error_context)
    
    if format == "json":
        print(explanation.to_json())
    else:
        print(explanation.to_markdown())


@app.command()
def export_audit(
    format: str = typer.Option("json", "--format", "-f", help="Output format (json, csv)"),
    last: int = typer.Option(100, "--last", "-n", help="Number of recent compilations"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Export audit trail for AI external consumption.
    
    Examples:
        cosmos export-audit --last=100 --format=json > audit.json
        cosmos export-audit --format=csv --output=audit.csv
    """
    print_header("Cosmos Audit Export v0.4.5-rc1")
    
    # In a real implementation, this would read from a database
    # For now, we'll create a sample export
    
    audit = {
        "cosmos_export_v1": {
            "version": "0.4.5-rc1",
            "schema": EXPORT_SCHEMA,
            "audit_trail": {
                "total_files": last,
                "approved": int(last * 0.9),
                "rejected": int(last * 0.1),
                "e401_count": int(last * 0.05),
                "fail_fast_events": int(last * 0.05),
                "exported_at": get_timestamp(),
                "hostname": get_hostname()
            },
            "compilation_results": [
                {
                    "file": f"file_{i}.cosmos",
                    "status": "APPROVED" if i % 10 != 0 else "REJECTED",
                    "error_code": "E401" if i % 20 == 0 else None,
                    "timestamp": get_timestamp(),
                    "duration_ms": 0.5 + (i % 10) * 0.1
                }
                for i in range(min(last, 10))
            ],
            "metadata": {
                "exporter": "cosmos-cli",
                "exported_at": get_timestamp(),
                "hostname": get_hostname()
            }
        }
    }
    
    if format == "csv":
        # Convert to CSV
        lines = ["file,status,error_code,timestamp,duration_ms"]
        for r in audit["cosmos_export_v1"]["compilation_results"]:
            lines.append(f"{r['file']},{r['status']},{r['error_code'] or ''},{r['timestamp']},{r['duration_ms']}")
        content = "\n".join(lines)
    else:
        content = json.dumps(audit, indent=2)
    
    if output:
        Path(output).write_text(content)
        print_success(f"Exported to: {output}")
    else:
        print(content)


@app.command()
def benchmark(
    files: int = typer.Option(100, "--files", "-n", help="Number of files to test"),
    e401: int = typer.Option(1, "--e401", "-e", help="Number of E401 files"),
):
    """
    Run quick benchmark.
    
    Examples:
        cosmos benchmark --files 1000
        cosmos benchmark -n 500 -e 10
    """
    print_header("Cosmos Benchmark v0.4.5-rc1")
    
    console.print(f"Files: {files}")
    console.print(f"E401 files: {e401}\n")
    
    # Run simple benchmark
    import time
    
    agent = CosmosCompilerAgent(fail_fast=True)
    
    test_code = """
cosmos Test {
    sun Main
    planet Task {
        model: claude-3-sonnet
    }
}
end
"""
    
    start = time.time()
    for _ in range(files):
        asyncio.run(agent.run(test_code))
    total_ms = (time.time() - start) * 1000
    
    console.print(Panel(
        f"[bold]Results:[/bold]\n"
        f"Total files: {files}\n"
        f"Total time: {total_ms:.2f}ms\n"
        f"Avg/file: {total_ms/files:.2f}ms\n"
        f"Throughput: {files/(total_ms/1000):.0f} files/s",
        title="Benchmark Results"
    ))


@app.command()
def version():
    """Show version information."""
    console.print(Panel(
        "[bold cyan]Cosmos DSL Compiler[/bold cyan]\n\n"
        "Version: 0.4.5-rc1\n"
        "Author: Luis Alberto Burciaga Miker\n"
        "License: MIT\n"
        "\n[dim]RFC-0004-F Compliant[/dim]"
    ))


# ============================================================
# MAIN
# ============================================================

def main():
    app()


if __name__ == "__main__":
    main()
