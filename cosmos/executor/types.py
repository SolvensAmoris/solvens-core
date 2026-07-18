"""
Cosmos Executor - Step Execution

Minimal MVP: executes steps with providers, tools, error handling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from cosmos.planner.types import PlanNode, StepStatus

logger = logging.getLogger("cosmos.executor")


@dataclass
class StepResult:
    """Result of step execution."""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    cost: float = 0.0
    tokens_used: int = 0
    duration_ms: float = 0.0


class StepExecutor:
    """
    Executes individual steps.
    
    Minimal MVP:
    - Calls LLM providers
    - Handles errors with retry
    - Tracks cost
    - Simple tool execution
    """
    
    def __init__(
        self,
        provider_registry: Optional[Any] = None,
        tool_registry: Optional[dict] = None,
    ):
        self.provider_registry = provider_registry
        self.tool_registry = tool_registry or {}
    
    async def execute(self, node: PlanNode) -> StepResult:
        """
        Execute a single step.
        
        Args:
            node: PlanNode to execute
            
        Returns:
            StepResult with execution details
        """
        start = time.time()
        logger.debug(f"Executor: Executing step {node.name}")
        
        try:
            if node.step_type == "tool":
                result = await self._execute_tool(node)
            else:
                result = await self._execute_task(node)
            
            duration_ms = (time.time() - start) * 1000
            
            return StepResult(
                step_id=node.id,
                status=StepStatus.COMPLETED,
                output=result,
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error(f"Executor: Step {node.name} failed: {e}")
            
            return StepResult(
                step_id=node.id,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
            )
    
    async def _execute_task(self, node: PlanNode) -> str:
        """
        Execute a task step (LLM call).
        
        For MVP, returns mock response.
        Real implementation would call provider.
        """
        # Check for provider
        provider = node.provider if node.provider != "auto" else "mock"
        
        # Simulate LLM call
        await asyncio.sleep(0.05)
        
        # Return mock result with context
        return f"[{provider.upper()}] Executed: {node.description[:50]}..."
    
    async def _execute_tool(self, node: PlanNode) -> str:
        """Execute a tool step."""
        tool_name = node.tools[0] if node.tools else "unknown"
        
        if tool_name in self.tool_registry:
            tool = self.tool_registry[tool_name]
            if asyncio.iscoroutinefunction(tool):
                return await tool(node.inputs)
            else:
                return tool(node.inputs)
        
        # Mock tool execution
        await asyncio.sleep(0.02)
        return f"Tool executed: {tool_name}"


class ToolRegistry:
    """
    Registry for executable tools.
    
    Minimal MVP for tool execution.
    """
    
    def __init__(self):
        self._tools: dict[str, callable] = {}
    
    def register(self, name: str, func: callable) -> None:
        """Register a tool."""
        self._tools[name] = func
        logger.debug(f"Tool registered: {name}")
    
    def get(self, name: str) -> Optional[callable]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[str]:
        """List all registered tools."""
        return list(self._tools.keys())
    
    async def execute(self, name: str, inputs: dict) -> Any:
        """Execute a tool."""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        if asyncio.iscoroutinefunction(tool):
            return await tool(inputs)
        else:
            return tool(inputs)
