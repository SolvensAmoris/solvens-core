"""Cosmos Runtime module.

Interprets and executes Cosmos DAGs.
Coordinates execution, waits for dependencies, and synchronizes results.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from solvens.cosmos.dag import CosmosDAG, DAGNode, DAGNodeStatus
from solvens.cosmos.planner import ExecutionPlan, ExecutionPhase, PhaseStatus


class RuntimeStatus(Enum):
    """Status of the runtime."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExecutionContext:
    """Context for a single execution."""
    
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dag: CosmosDAG | None = None
    plan: ExecutionPlan | None = None
    status: RuntimeStatus = RuntimeStatus.IDLE
    started_at: datetime | None = None
    completed_at: datetime | None = None
    results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    callbacks: list[Callable] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results_count": len(self.results),
            "errors_count": len(self.errors),
        }


class CosmosRuntime:
    """Runtime for executing Cosmos DAGs.
    
    Responsibilities:
    - Interpret the DAG
    - Coordinate execution
    - Wait for dependencies
    - Synchronize results
    - Reconstruct output
    """
    
    def __init__(self):
        self.context: ExecutionContext | None = None
        self._executors: dict[str, Callable] = {}
        self._running_tasks: set[asyncio.Task] = set()
    
    def register_executor(self, operation: str, executor: Callable) -> None:
        """Register an executor for a specific operation type."""
        self._executors[operation] = executor
    
    async def execute(self, dag: CosmosDAG, plan: ExecutionPlan | None = None) -> ExecutionContext:
        """Execute a DAG according to the plan.
        
        Args:
            dag: The DAG to execute
            plan: Optional execution plan (will generate if not provided)
            
        Returns:
            ExecutionContext with results
        """
        self.context = ExecutionContext(dag=dag, plan=plan)
        self.context.started_at = datetime.utcnow()
        self.context.status = RuntimeStatus.RUNNING
        
        try:
            # Generate plan if not provided
            if plan is None:
                from solvens.cosmos.planner import CosmosPlanner
                planner = CosmosPlanner()
                plan = planner.plan(dag if dag.root else CosmosDAG())
                self.context.plan = plan
            
            # Execute phases in order
            for phase in plan.phases:
                await self._execute_phase(phase, dag)
                
                # Check if any phase failed
                if self.context.status == RuntimeStatus.FAILED:
                    break
            
            if self.context.status == RuntimeStatus.RUNNING:
                self.context.status = RuntimeStatus.COMPLETED
                
        except Exception as e:
            self.context.status = RuntimeStatus.FAILED
            self.context.errors["runtime"] = str(e)
        
        self.context.completed_at = datetime.utcnow()
        return self.context
    
    async def _execute_phase(self, phase: ExecutionPhase, dag: CosmosDAG) -> None:
        """Execute a single phase of the plan."""
        phase.status = PhaseStatus.RUNNING
        
        if phase.parallel:
            # Execute all nodes in parallel
            tasks = []
            for node_id in phase.nodes:
                node = dag.get_node(node_id)
                if node:
                    task = asyncio.create_task(self._execute_node(node, dag))
                    tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute nodes sequentially
            for node_id in phase.nodes:
                node = dag.get_node(node_id)
                if node:
                    await self._execute_node(node, dag)
        
        phase.status = PhaseStatus.COMPLETED
    
    async def _execute_node(self, node: DAGNode, dag: CosmosDAG) -> Any:
        """Execute a single node.
        
        The node's operation is delegated to the registered executor.
        """
        node.status = DAGNodeStatus.RUNNING
        node.started_at = datetime.utcnow()
        
        try:
            # Get input from dependencies
            inputs = self._collect_inputs(node, dag)
            
            # Get executor for this operation
            executor = self._executors.get(node.operation)
            
            if executor:
                # Execute with registered executor
                result = await executor(node, inputs, self.context)
            else:
                # Fallback to generic execution
                result = await self._generic_execute(node, inputs)
            
            # Store result
            self.context.results[node.id] = result
            node.outputs = result if isinstance(result, dict) else {"result": result}
            
            node.status = DAGNodeStatus.COMPLETED
            node.completed_at = datetime.utcnow()
            
            return result
            
        except Exception as e:
            node.status = DAGNodeStatus.FAILED
            self.context.errors[node.id] = str(e)
            self.context.status = RuntimeStatus.FAILED
            return None
    
    def _collect_inputs(self, node: DAGNode, dag: CosmosDAG) -> dict[str, Any]:
        """Collect inputs from dependency nodes."""
        inputs = node.inputs.copy()
        
        for dep_id in node.dependencies:
            dep_node = dag.get_node(dep_id)
            if dep_node and dep_id in self.context.results:
                inputs[dep_id] = self.context.results[dep_id]
        
        return inputs
    
    async def _generic_execute(self, node: DAGNode, inputs: dict[str, Any]) -> Any:
        """Generic execution for nodes without specific executors.
        
        This creates a task representation that can be executed by SOLVENS CORE.
        """
        return {
            "task": node.operation,
            "node_id": node.id,
            "node_name": node.name,
            "provider": node.provider,
            "agent": node.agent,
            "tool": node.tool,
            "inputs": inputs,
            "status": "ready_for_execution",
        }
    
    def get_results(self) -> dict[str, Any]:
        """Get execution results."""
        if not self.context:
            return {}
        return self.context.results
    
    def get_errors(self) -> dict[str, str]:
        """Get execution errors."""
        if not self.context:
            return {}
        return self.context.errors
    
    def get_progress(self) -> dict[str, Any]:
        """Get execution progress."""
        if not self.context or not self.context.dag:
            return {}
        
        dag = self.context.dag
        stats = dag.get_statistics()
        
        return {
            "status": self.context.status.value,
            "total_nodes": stats["total_nodes"],
            "completed": stats["status"]["completed"],
            "running": stats["status"]["running"],
            "failed": stats["status"]["failed"],
            "pending": stats["status"]["pending"],
            "progress_percent": (
                stats["status"]["completed"] / stats["total_nodes"] * 100
                if stats["total_nodes"] > 0 else 0
            ),
        }
    
    async def pause(self) -> None:
        """Pause execution."""
        if self.context:
            self.context.status = RuntimeStatus.PAUSED
            for task in self._running_tasks:
                task.cancel()
    
    async def resume(self) -> None:
        """Resume execution."""
        if self.context and self.context.status == RuntimeStatus.PAUSED:
            self.context.status = RuntimeStatus.RUNNING
            # Continue execution...
    
    async def cancel(self) -> None:
        """Cancel execution."""
        if self.context:
            for task in self._running_tasks:
                task.cancel()
            self.context.status = RuntimeStatus.FAILED
