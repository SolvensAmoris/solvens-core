"""Cosmos Executor module.

Executes Cosmos tasks through SOLVENS CORE's Agent Orchestrator.
Bridges the gap between Cosmos DAG nodes and provider execution.
"""

from __future__ import annotations

from typing import Any

from solvens.cosmos.dag import DAGNode, DAGNodeStatus
from solvens.cosmos.runtime import ExecutionContext


class CosmosExecutor:
    """Executes Cosmos DAG nodes through SOLVENS CORE.
    
    This executor:
    - Takes Cosmos nodes
    - Converts them to Agent tasks
    - Routes through Capability Router
    - Executes via providers
    """
    
    def __init__(self, orchestrator=None, router=None):
        """Initialize executor with optional orchestrator and router."""
        self.orchestrator = orchestrator
        self.router = router
        self._execution_cache: dict[str, Any] = {}
    
    async def execute_node(self, node: DAGNode, inputs: dict[str, Any], context: ExecutionContext) -> Any:
        """Execute a single Cosmos node through SOLVENS CORE.
        
        Args:
            node: The Cosmos DAG node to execute
            inputs: Input data from dependencies
            context: Execution context
            
        Returns:
            Execution result
        """
        # Build task description
        task_desc = self._build_task_description(node, inputs)
        
        # Determine execution strategy
        provider = node.provider
        agent = node.agent
        tool = node.tool
        
        # Execute through orchestrator if available
        if self.orchestrator:
            return await self._execute_via_orchestrator(
                task_desc, provider, agent, tool, inputs
            )
        
        # Fallback to direct execution
        return await self._execute_direct(node, inputs)
    
    def _build_task_description(self, node: DAGNode, inputs: dict[str, Any]) -> str:
        """Build a natural language task description from the node."""
        parts = []
        
        if node.name:
            parts.append(f"Task: {node.name}")
        
        if node.operation:
            parts.append(f"Operation: {node.operation}")
        
        if node.tool:
            parts.append(f"Use tool: {node.tool}")
        
        if inputs:
            parts.append(f"Inputs: {inputs}")
        
        return "\n".join(parts) if parts else node.operation
    
    async def _execute_via_orchestrator(
        self,
        task_desc: str,
        provider: str | None,
        agent: str | None,
        tool: str | None,
        inputs: dict[str, Any]
    ) -> Any:
        """Execute task through Agent Orchestrator."""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
        
        # Submit task to orchestrator
        callback = self._create_callback(provider, agent, tool)
        
        task_id = await self.orchestrator.submit_task(
            description=task_desc,
            callback=callback,
        )
        
        # Wait for task to complete
        task = self.orchestrator.get_task(task_id)
        
        # Wait for completion
        while task.status.value in ("pending", "running"):
            import asyncio
            await asyncio.sleep(0.1)
            task = self.orchestrator.get_task(task_id)
        
        return {
            "task_id": task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
        }
    
    def _create_callback(self, provider: str | None, agent: str | None, tool: str | None):
        """Create a callback function for the task."""
        async def callback():
            return {
                "provider": provider,
                "agent": agent,
                "tool": tool,
            }
        return callback
    
    async def _execute_direct(self, node: DAGNode, inputs: dict[str, Any]) -> Any:
        """Direct execution without orchestrator.
        
        Returns a structured result that can be executed later.
        """
        return {
            "cosmos_node_id": node.id,
            "cosmos_node_name": node.name,
            "operation": node.operation,
            "provider": node.provider,
            "agent": node.agent,
            "tool": node.tool,
            "inputs": inputs,
            "status": "pending_execution",
            "execution_plan": {
                "step_1": "Route to appropriate provider",
                "step_2": "Execute via provider",
                "step_3": "Return result",
            }
        }
    
    def get_capabilities(self) -> dict[str, list[str]]:
        """Get available execution capabilities."""
        return {
            "providers": ["openai", "anthropic", "ollama", "google", "deepseek"],
            "agents": ["default", "coder", "researcher", "writer"],
            "tools": ["python", "bash", "web_search", "file_operations"],
        }
