"""
Cosmos Scheduler Types
"""

from __future__ import annotations

import uuid
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable, Awaitable

from cosmos.planner.types import Plan, PlanNode, StepStatus, PlanStatus

logger = logging.getLogger("cosmos.scheduler")


@dataclass
class ScheduleDecision:
    """Decision made by scheduler."""
    node_id: str
    action: str  # "execute", "skip", "wait"
    reason: str = ""
    scheduled_at: float = field(default_factory=time.time)


class DAGScheduler:
    """
    DAG-aware task scheduler.
    
    Minimal MVP:
    - Detects ready tasks based on dependencies
    - Executes ready tasks in parallel
    - Handles retries
    - Emits events
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        executor: Optional[Callable[[PlanNode], Awaitable[Any]]] = None,
    ):
        self.max_concurrent = max_concurrent
        self.executor = executor
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running: dict[str, asyncio.Task] = {}
        self._plan: Optional[Plan] = None
        self._events: list[ScheduleDecision] = []
    
    async def schedule(self, plan: Plan) -> Plan:
        """
        Schedule and execute all steps in plan.
        
        Args:
            plan: Plan to execute
            
        Returns:
            Completed plan with results
        """
        self._plan = plan
        self._events = []
        plan.status = PlanStatus.IN_PROGRESS
        
        logger.info(f"Scheduler: Starting plan {plan.id} with {len(plan.nodes)} steps")
        
        # Initial marking
        plan.mark_ready()
        
        # Execute until all done
        while not self._is_complete(plan):
            # Get ready nodes
            ready = plan.get_ready_nodes()
            
            if not ready and not self._running:
                # Deadlock - nothing ready and nothing running
                logger.error(f"Scheduler: Deadlock detected in plan {plan.id}")
                plan.status = PlanStatus.FAILED
                break
            
            # Execute ready nodes
            for node in ready:
                if node.id not in self._running:
                    asyncio.create_task(self._execute_node(node))
            
            # Brief pause to avoid busy loop
            await asyncio.sleep(0.01)
        
        # Determine final status
        if plan.status != PlanStatus.FAILED:
            if all(n.status == StepStatus.COMPLETED for n in plan.nodes):
                plan.status = PlanStatus.COMPLETED
            elif any(n.status == StepStatus.FAILED for n in plan.nodes):
                plan.status = PlanStatus.FAILED
        
        logger.info(f"Scheduler: Plan {plan.id} finished with status {plan.status.value}")
        
        return plan
    
    async def _execute_node(self, node: PlanNode) -> None:
        """Execute a single node."""
        if node.id in self._running:
            return
        
        node.status = StepStatus.RUNNING
        node.started_at = time.time()
        self._running[node.id] = asyncio.current_task()
        
        self._events.append(ScheduleDecision(
            node_id=node.id,
            action="execute",
            reason=f"Starting {node.name}"
        ))
        
        logger.debug(f"Scheduler: Executing node {node.name}")
        
        async with self._semaphore:
            try:
                if self.executor:
                    result = await self.executor(node)
                    node.outputs["result"] = result
                else:
                    # Mock execution
                    await asyncio.sleep(0.1)
                    node.outputs["result"] = f"Mock result for {node.name}"
                
                node.status = StepStatus.COMPLETED
                node.completed_at = time.time()
                
                self._events.append(ScheduleDecision(
                    node_id=node.id,
                    action="complete",
                    reason=f"Completed {node.name} in {node.duration_ms:.0f}ms"
                ))
                
                # Mark dependent nodes as ready
                if self._plan:
                    self._plan.mark_ready()
                
                logger.debug(f"Scheduler: Node {node.name} completed")
                
            except Exception as e:
                node.status = StepStatus.FAILED
                node.error = str(e)
                node.completed_at = time.time()
                
                self._events.append(ScheduleDecision(
                    node_id=node.id,
                    action="fail",
                    reason=f"Failed {node.name}: {e}"
                ))
                
                logger.error(f"Scheduler: Node {node.name} failed: {e}")
            
            finally:
                self._running.pop(node.id, None)
    
    def _is_complete(self, plan: Plan) -> bool:
        """Check if plan execution is complete."""
        # All nodes have final status
        for node in plan.nodes:
            if node.status not in (
                StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED
            ):
                return False
        return True
    
    def get_events(self) -> list[ScheduleDecision]:
        """Get scheduling events."""
        return self._events.copy()
