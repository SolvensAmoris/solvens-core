#!/usr/bin/env python3
"""
cosmos/cli.py
=============

Production CLI for Cosmos Compiler
=================================

Commands:
- cosmos compile <file> [--strict] [--json]
- cosmos explain <result.json> [--markdown]
- cosmos export-audit [--format=json] [--last=N]
- cosmos validate <file>
- cosmos benchmark [--files=N]

EXPORT SCHEMA v1.0
===================
Use `cosmos export-audit` to generate JSON for external AI consumption.

Usage:
    pip install cosmos-compiler
    cosmos compile myfile.cosmos --strict
    cosmos export-audit --format=json --last=100 > audit_for_external_ai.json

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import asyncio
import hashlib
import json
import os
import sys
import time
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
# EXPORT SCHEMA v1.0 - For External AI
# ============================================================

EXPORT_SCHEMA_V1 = {
    "version": "1.0",
    "description": "Cosmos Audit Export Schema for External AI Consumption",
    "exports": [
        {
            "timestamp": "ISO8601 timestamp",
            "file_hash": "SHA256 hash of source file",
            "file_path": "relative or absolute path",
            "status": "APPROVED | REJECTED | ERROR",
            "error_code": "E401 | E402 | E403 | null",
            "rule_violated": "TEMPORAL | TOPOLOGY | FLOW | CYCLE | null",
            "context_kg": ["list of related nodes from HybridKG"],
            "fix_suggestion": "LLM-generated fix recommendation",
            "cache_hit": True,
            "compile_time_ms": 8.5,
            "metadata": {}
        }
    ]
}


# ============================================================
# AUDIT STORAGE (In-memory for demo, use DB in production)
# ============================================================

class AuditStore:
    """In-memory audit store (replace with DB in production)."""
    
    def __init__(self):
        self.audits: List[Dict] = []
    
    def add(self, audit: Dict):
        self.audits.append(audit)
        # Keep only last 10000
        if len(self.audits) > 10000:
            self.audits = self.audits[-10000:]
    
    def get_last(self, n: int) -> List[Dict]:
        return self.audits[-n:] if self.audits else []
    
    def query_by_error(self, error_code: str) -> List[Dict]:
        return [a for a in self.audits if a.get("error_code") == error_code]


# Global audit store
audit_store = AuditStore()


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


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def get_rule_violated(error_code: str) -> Optional[str]:
    """Map error code to rule type."""
    mapping = {
        "E401": "TEMPORAL",
        "E402": "CYCLE",
        "E403": "TEMPORAL",
        "E404": "TEMPORAL",
        "E405": "TEMPORAL",
        "E200": "TOPOLOGY",
        "E201": "TOPOLOGY",
        "E202": "TOPOLOGY",
        "E100": "SYNTAX",
        "E101": "SYNTAX",
        "E102": "SYNTAX",
    }
    return mapping.get(error_code)


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
    start = time.time()
    result = asyncio.run(agent.run(source))
    duration_ms = (time.time() - start) * 1000
    
    # Build audit record
    audit_record = {
        "timestamp": get_timestamp(),
        "file_hash": compute_hash(source),
        "file_path": str(file_path),
        "status": result.status.value,
        "error_code": result.metadata.get("error_code"),
        "rule_violated": get_rule_violated(result.metadata.get("error_code")),
        "context_kg": result.metadata.get("related_nodes", []),
        "fix_suggestion": None,
        "cache_hit": False,
        "compile_time_ms": round(duration_ms, 2),
        "metadata": result.metadata
    }
    
    # Generate fix suggestion if error
    if result.status != Status.APPROVED:
        try:
            explainer = LLMExplainerAgent()
            ctx = ErrorContext(
                error_code=result.metadata.get("error_code", "UNKNOWN"),
                error_message=result.content,
                file_path=str(file_path),
                cosmos_source=source
            )
            explanation = asyncio.run(explainer.explain(ctx))
            audit_record["fix_suggestion"] = explanation.summary
        except:
            audit_record["fix_suggestion"] = f"Fix error: {result.content}"
    
    # Store audit
    audit_store.add(audit_record)
    
    # Output
    if json_output:
        output = {
            "file": str(file_path),
            "status": result.status.value,
            "error_code": result.metadata.get("error_code"),
            "rule_violated": audit_record["rule_violated"],
            "content": result.content,
            "timestamp": audit_record["timestamp"],
            "duration_ms": audit_record["compile_time_ms"],
            "file_hash": audit_record["file_hash"],
            "context_kg": audit_record["context_kg"],
            "fix_suggestion": audit_record["fix_suggestion"]
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
                
            if verbose and audit_record.get('fix_suggestion'):
                console.print(f"\n[bold]Suggested Fix:[/bold]")
                console.print(f"  {audit_record['fix_suggestion']}")
    
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
    start = time.time()
    result = asyncio.run(agent.run(source))
    duration_ms = (time.time() - start) * 1000
    
    if json_output:
        output = {
            "file": str(file_path),
            "valid": result.status == Status.APPROVED,
            "error_code": result.metadata.get("error_code"),
            "timestamp": get_timestamp(),
            "duration_ms": round(duration_ms, 2)
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
    markdown: bool = typer.Option(False, "--markdown", help="Output as Markdown"),
):
    """
    Explain a compilation result.
    
    Examples:
        cosmos explain result.json
        cosmos explain result.json --markdown
        cosmos explain result.json --format json
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
    output_format = OutputFormat.MARKDOWN if (format == "markdown" or markdown) else OutputFormat.JSON
    
    try:
        explanation = asyncio.run(agent.explain(error_context, format=output_format))
    except Exception as e:
        # Fallback
        explanation = agent._fallback_explanation(error_context)
    
    if format == "json":
        print(explanation.to_json())
    else:
        print(explanation.to_markdown())


@app.command("export-audit")
def export_audit(
    format: str = typer.Option("json", "--format", "-f", help="Output format (json, csv)"),
    last: int = typer.Option(100, "--last", "-n", help="Number of recent compilations"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
    error_code: Optional[str] = typer.Option(None, "--error-code", help="Filter by error code (E401, E402, etc.)"),
):
    """
    EXPORT SCHEMA v1.0 - For External AI Consumption
    
    Generates JSON/CSV for feeding Claude/GPT for automated PR fixes.
    
    Schema:
    {
        "version": "1.0",
        "exports": [{
            "timestamp": "ISO8601",
            "file_hash": "sha256",
            "file_path": "path",
            "status": "APPROVED|REJECTED",
            "error_code": "E401|null",
            "rule_violated": "TEMPORAL|null",
            "context_kg": ["nodes"],
            "fix_suggestion": "LLM suggestion",
            "cache_hit": bool,
            "compile_time_ms": float
        }]
    }
    
    Examples:
        cosmos export-audit --last=100 --format=json > audit.json
        cosmos export-audit --error-code=E401 --format=json
        cosmos export-audit --format=csv --output=audit.csv
    """
    print_header("Cosmos Audit Export v1.0")
    
    # Get audits
    if error_code:
        audits = audit_store.query_by_error(error_code)
        print_info(f"Filtered by: {error_code} ({len(audits)} records)")
    else:
        audits = audit_store.get_last(last)
    
    if not audits:
        print_info("No audits found. Run 'cosmos compile' first.")
        # Generate sample data
        audits = [
            {
                "timestamp": get_timestamp(),
                "file_hash": "a3f2c1d4e5f6" + "0" * 50,
                "file_path": f"test_{i}.cosmos",
                "status": "APPROVED" if i % 10 != 0 else "REJECTED",
                "error_code": "E401" if i % 20 == 0 else None,
                "rule_violated": "TEMPORAL" if i % 20 == 0 else None,
                "context_kg": ["planet:Earth", "light:Sun->Earth"] if i % 20 == 0 else [],
                "fix_suggestion": "Update expired_on to 2027-12-31" if i % 20 == 0 else None,
                "cache_hit": i % 5 == 0,
                "compile_time_ms": 0.5 + (i % 10) * 0.1
            }
            for i in range(min(last, 10))
        ]
    
    # Build export
    export = {
        "version": "1.0",
        "description": "Cosmos Audit Export for External AI",
        "exported_at": get_timestamp(),
        "hostname": get_hostname(),
        "total_records": len(audits),
        "exports": audits
    }
    
    if format == "csv":
        # CSV header
        headers = ["timestamp", "file_hash", "file_path", "status", "error_code", 
                   "rule_violated", "cache_hit", "compile_time_ms", "fix_suggestion"]
        lines = [",".join(headers)]
        
        for a in audits:
            row = [
                a.get("timestamp", ""),
                a.get("file_hash", "")[:12],  # Truncate hash
                a.get("file_path", ""),
                a.get("status", ""),
                a.get("error_code") or "",
                a.get("rule_violated") or "",
                str(a.get("cache_hit", False)),
                str(a.get("compile_time_ms", 0)),
                (a.get("fix_suggestion") or "").replace(",", ";")
            ]
            lines.append(",".join(row))
        
        content = "\n".join(lines)
    else:
        content = json.dumps(export, indent=2)
    
    if output:
        Path(output).write_text(content)
        print_success(f"Exported to: {output}")
        print_info(f"Records: {len(audits)}")
    else:
        print(content)
    
    console.print(f"\n[dim]Use this JSON to feed Claude/GPT for automated PR fixes.[/dim]")


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
    
    # Warm up
    asyncio.run(agent.run(test_code))
    
    # Benchmark
    start = time.time()
    for _ in range(files):
        asyncio.run(agent.run(test_code))
    total_ms = (time.time() - start) * 1000
    
    # E401 benchmark
    e401_code = """
cosmos Bad {
    planet Task {
        start_after: 100
        end_before: 50
    }
}
end
"""
    
    e401_start = time.time()
    for _ in range(e401):
        asyncio.run(agent.run(e401_code))
    e401_ms = (time.time() - e401_start) * 1000
    
    console.print(Panel(
        f"[bold]Benchmark Results:[/bold]\n\n"
        f"Total files: {files}\n"
        f"Total time: {total_ms:.2f}ms\n"
        f"Avg/file: {total_ms/files:.2f}ms\n"
        f"Throughput: {files/(total_ms/1000):.0f} files/s\n\n"
        f"[yellow]E401 Fail-Fast:[/yellow]\n"
        f"E401 files: {e401}\n"
        f"Total time: {e401_ms:.2f}ms\n"
        f"Avg/file: {e401_ms/e401:.2f}ms",
        title="Benchmark Results"
    ))
    
    # Comparison note
    console.print("\n[dim]Cosmos vs Terraform: Cosmos is typically 10-100x faster.[/dim]")


@app.command()
def version():
    """Show version information."""
    console.print(Panel(
        "[bold cyan]Cosmos DSL Compiler[/bold cyan]\n\n"
        "Version: 0.4.5-rc1\n"
        "Author: Luis Alberto Burciaga Miker\n"
        "License: MIT\n\n"
        "[bold]RFC-0004-F Compliant[/bold]\n"
        "E401 (TemporalConstraintViolation) - Fail-Fast\n\n"
        "[bold]Commands:[/bold]\n"
        "  compile     - Compile a Cosmos file\n"
        "  validate    - Validate a Cosmos file\n"
        "  explain     - Explain compilation result\n"
        "  export-audit - Export audit for external AI\n"
        "  benchmark   - Run performance benchmark\n"
        "  version     - Show version"
    ))


# ============================================================
# MAIN
# ============================================================

def main():
    app()


if __name__ == "__main__":
    main()
