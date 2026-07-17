"""
streaming.py - Real-time Streaming for CLI
=========================================

Provides streaming output for CLI with real-time cost tracking.
"""

import asyncio
import sys
import time
from typing import AsyncIterator, Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class OutputMode(Enum):
    """Output mode for streaming."""
    STREAM = "stream"      # Live streaming
    BLOCK = "block"        # Wait for complete response
    DELTA = "delta"        # Show token deltas


@dataclass
class StreamStats:
    """Statistics for a streaming response."""
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    elapsed_seconds: float = 0.0
    provider: str = ""
    model: str = ""
    estimated_cost: float = 0.0
    
    def update(self, tokens: int, elapsed: float):
        self.tokens_generated = tokens
        self.elapsed_seconds = elapsed
        self.tokens_per_second = tokens / max(elapsed, 0.001)


class StreamingResponse:
    """
    Streaming response handler with real-time display.
    
    Usage:
        async for chunk in stream.chat("Hello"):
            print(chunk, end="", flush=True)
    """
    
    def __init__(
        self,
        mode: OutputMode = OutputMode.STREAM,
        show_stats: bool = True,
        cost_tracker = None,
        console = None
    ):
        self.mode = mode
        self.show_stats = show_stats
        self.cost_tracker = cost_tracker
        self.console = console or (Console() if RICH_AVAILABLE else None)
        
        self._buffer = ""
        self._start_time = 0
        self._tokens = 0
        self._request_id: Optional[str] = None
    
    def __aiter__(self):
        return self
    
    async def __anext__(self) -> str:
        raise StopAsyncIteration
    
    def start(self, provider: str = "", model: str = "") -> str:
        """Start streaming session."""
        self._start_time = time.time()
        self._tokens = 0
        self._request_id = self.cost_tracker.start_request(
            provider=provider,
            model=model,
            operation="stream"
        ) if self.cost_tracker else None
        
        return self._request_id or ""
    
    def add_token(self, token: str) -> float:
        """Add a token and update stats."""
        self._buffer += token
        self._tokens += 1
        
        # Update cost tracker
        cost = 0.0
        if self.cost_tracker and self._request_id:
            cost = self.cost_tracker.add_output_token(self._request_id)
        
        return cost
    
    def end(self) -> Dict[str, Any]:
        """End streaming session."""
        elapsed = time.time() - self._start_time
        stats = StreamStats(
            tokens_generated=self._tokens,
            tokens_per_second=self._tokens / max(elapsed, 0.001),
            elapsed_seconds=elapsed,
            estimated_cost=0.0  # Calculated by tracker
        )
        
        return {
            "buffer": self._buffer,
            "tokens": self._tokens,
            "elapsed": elapsed,
            "tokens_per_second": stats.tokens_per_second
        }


class StreamingDisplay:
    """
    Real-time display for streaming responses.
    
    Shows:
    - Live token count
    - Tokens per second
    - Elapsed time
    - Provider/Model info
    - Cost estimate
    """
    
    def __init__(self, console = None, show_panel: bool = True):
        self.console = console or (Console() if RICH_AVAILABLE else None)
        self.show_panel = show_panel
        self._live = None
        self._tokens = 0
        self._start_time = 0
        self._provider = ""
        self._model = ""
    
    def start(self, provider: str = "", model: str = ""):
        """Start the live display."""
        if not self.console:
            return
        
        self._start_time = time.time()
        self._provider = provider
        self._model = model
        self._tokens = 0
        
        if self.show_panel and RICH_AVAILABLE:
            self._live = Live(self._make_panel(), console=self.console, refresh_per_second=10)
            self._live.start()
    
    def update(self, token: str):
        """Update display with new token."""
        self._tokens += 1
        
        if self._live and RICH_AVAILABLE:
            self._live.update(self._make_panel())
        elif self.console and not RICH_AVAILABLE:
            # Fallback: simple progress
            elapsed = time.time() - self._start_time
            tps = self._tokens / max(elapsed, 0.001)
            sys.stdout.write(f"\rTokens: {self._tokens} | TPS: {tps:.1f} | {elapsed:.1f}s")
            sys.stdout.flush()
    
    def end(self):
        """End the live display."""
        if self._live and RICH_AVAILABLE:
            self._live.stop()
            self.console.print("\n")
        elif self.console and not RICH_AVAILABLE:
            elapsed = time.time() - self._start_time
            tps = self._tokens / max(elapsed, 0.001)
            self.console.print(f"\n[dim]Completed: {self._tokens} tokens in {elapsed:.1f}s ({tps:.1f} tps)[/dim]")
    
    def _make_panel(self) -> Panel:
        """Create status panel."""
        if not RICH_AVAILABLE:
            return Panel("")
        
        elapsed = time.time() - self._start_time
        tps = self._tokens / max(elapsed, 0.001)
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan")
        table.add_column(style="white")
        
        table.add_row("Tokens:", f"[bold]{self._tokens}[/bold]")
        table.add_row("Speed:", f"{tps:.1f} t/s")
        table.add_row("Time:", f"{elapsed:.1f}s")
        if self._provider:
            table.add_row("Provider:", f"[dim]{self._provider}[/dim]")
        if self._model:
            table.add_row("Model:", f"[dim]{self._model}[/dim]")
        
        return Panel(
            table,
            title="[bold]Generating...[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )


async def stream_chat(
    messages: list,
    provider: str = "openai",
    model: str = "gpt-4",
    api_key: Optional[str] = None,
    cost_tracker = None,
    stream_display: bool = True,
    callback: Optional[Callable[[str], None]] = None
) -> str:
    """
    Stream chat completion with real-time display.
    
    Usage:
        result = await stream_chat(
            messages=[{"role": "user", "content": "Hello!"}],
            provider="openai",
            model="gpt-4"
        )
    """
    display = StreamingDisplay(show_panel=stream_display) if RICH_AVAILABLE else None
    response = StreamingResponse(
        mode=OutputMode.STREAM,
        cost_tracker=cost_tracker
    )
    
    response.start(provider=provider, model=model)
    if display:
        display.start(provider=provider, model=model)
    
    try:
        # Simulated streaming (replace with actual API call)
        full_response = await _simulated_stream(messages, model, callback)
        
        for char in full_response:
            response.add_token(char)
            if display:
                display.update(char)
            if callback:
                callback(char)
            # Small delay for visual effect
            await asyncio.sleep(0.01)
        
    finally:
        result = response.end()
        if display:
            display.end()
    
    return result["buffer"]


async def _simulated_stream(
    messages: list,
    model: str,
    callback: Optional[Callable] = None
) -> str:
    """Simulated streaming for demo."""
    
    responses = {
        "gpt-4": "GPT-4 response: This is a simulated streaming response from GPT-4. In production, this would be a real API call.",
        "claude-3-sonnet": "Claude 3 Sonnet response: This is a simulated streaming response from Claude 3 Sonnet. In production, this would be a real API call.",
        "default": "Response: This is a simulated streaming response. Configure your API keys for real providers."
    }
    
    response_text = responses.get(model, responses["default"])
    
    # Simular delay de red
    await asyncio.sleep(0.1)
    
    return response_text


# ============================================================
# CLI Command
# ============================================================

async def chat_command(
    prompt: str,
    provider: str = "openai",
    model: str = "gpt-4",
    stream: bool = True,
    show_costs: bool = True
):
    """
    CLI chat command with streaming.
    
    Usage:
        await chat_command("Hello!", provider="openai", model="gpt-4", stream=True)
    """
    from .cost_tracker import CostTracker
    
    tracker = CostTracker() if show_costs else None
    
    messages = [{"role": "user", "content": prompt}]
    
    if stream:
        result = await stream_chat(
            messages=messages,
            provider=provider,
            model=model,
            cost_tracker=tracker,
            stream_display=True
        )
    else:
        result = await stream_chat(
            messages=messages,
            provider=provider,
            model=model,
            cost_tracker=tracker,
            stream_display=False
        )
        print(result)
    
    if tracker and show_costs:
        from .cost_tracker import format_stats, format_cost
        print("\n" + format_stats(tracker.get_stats()))
        print(f"\nTotal Cost: {format_cost(tracker.get_total_cost())}")


# ============================================================
# Demo
# ============================================================

async def demo():
    """Demo de streaming."""
    print("=" * 60)
    print("STREAMING DEMO")
    print("=" * 60)
    
    from .cost_tracker import CostTracker
    
    tracker = CostTracker()
    
    print("\n[Streaming response from GPT-4...]")
    print()
    
    result = await stream_chat(
        messages=[{"role": "user", "content": "Explain quantum computing in 2 sentences."}],
        provider="openai",
        model="gpt-4",
        cost_tracker=tracker,
        stream_display=True
    )
    
    print("\n")
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)
    
    from .cost_tracker import format_stats, format_cost
    print("\n" + format_stats(tracker.get_stats()))


if __name__ == "__main__":
    asyncio.run(demo())
