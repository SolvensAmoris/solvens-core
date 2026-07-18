"""
Cosmos Engine - Complete Orchestration

Ties together: Planner → Scheduler → Executor
Minimal MVP for end-to-end task execution.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from cosmos.planner.types import Plan, PlanNode, PlanStatus, StepStatus
from cosmos.planner import LLMPlanner
from cosmos.scheduler import DAGScheduler
from cosmos.executor import StepExecutor, ToolRegistry

logger = logging.getLogger("cosmos.engine")


@dataclass
class EngineConfig:
    """Configuration for the engine."""
    max_concurrent: int = 5
    default_timeout: float = 60.0
    max_retries: int = 3
    enable_audit: bool = True


class Engine:
    """
    Complete orchestration engine.
    
    Minimal MVP that provides:
    - Plan creation from natural language
    - DAG-aware parallel execution
    - Step execution with providers
    - Basic error handling
    - Audit logging
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        
        # Components
        self.planner = LLMPlanner()
        self.scheduler = DAGScheduler(max_concurrent=self.config.max_concurrent)
        self.executor = StepExecutor()
        self.tools = ToolRegistry()
        
        # Audit log
        self._audit: list[dict] = []
        
        # Connect scheduler to executor
        async def execute_step(node: PlanNode) -> Any:
            result = await self.executor.execute(node)
            self._log_audit({
                "event": "step_complete",
                "step_id": node.id,
                "step_name": node.name,
                "status": result.status.value,
            })
            return result.output
        
        self.scheduler.executor = execute_step
        
        logger.info(f"Engine initialized (max_concurrent={self.config.max_concurrent})")
    
    async def run(self, task: str) -> Plan:
        """
        Run a task end-to-end.
        
        Args:
            task: Natural language task description
            
        Returns:
            Completed plan with results
        """
        start = time.time()
        
        self._log_audit({"event": "task_start", "task": task})
        
        try:
            # 1. Create plan
            logger.info(f"Engine: Creating plan for: {task[:100]}")
            plan = await self.planner.create_plan(task)
            
            # 2. Execute plan
            logger.info(f"Engine: Executing plan with {len(plan.nodes)} steps")
            result = await self.scheduler.schedule(plan)
            
            # 3. Return completed plan
            duration_ms = (time.time() - start) * 1000
            self._log_audit({
                "event": "task_complete",
                "task": task,
                "plan_id": plan.id,
                "status": result.status.value,
                "duration_ms": duration_ms,
            })
            
            logger.info(f"Engine: Task complete in {duration_ms:.0f}ms, status={result.status.value}")
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error(f"Engine: Task failed: {e}")
            self._log_audit({
                "event": "task_error",
                "task": task,
                "error": str(e),
                "duration_ms": duration_ms,
            })
            raise
    
    def _log_audit(self, entry: dict) -> None:
        """Log audit entry."""
        if not self.config.enable_audit:
            return
        
        entry["timestamp"] = time.time()
        self._audit.append(entry)
    
    def get_audit_log(self) -> list[dict]:
        """Get audit log."""
        return self._audit.copy()
    
    def clear_audit(self) -> None:
        """Clear audit log."""
        self._audit.clear()


# Singleton for convenience
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get or create singleton engine."""
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine


async def run_task(task: str) -> Plan:
    """Convenience function to run a single task."""
    engine = get_engine()
    return await engine.run(task)
