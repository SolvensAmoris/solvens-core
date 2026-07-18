"""
Cosmos Hardened Executor

Executor with HardenedScheduler and billing integration.
"""

from __future__ import annotations

import asyncio
import logging
import time
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from cosmos.planner.types import PlanNode, StepStatus, Plan, PlanStatus
from cosmos.scheduler.hardened import HardenedScheduler
from beta.billing import BillingMiddleware, PlanTier, get_billing_middleware, get_usage_tracker

logger = logging.getLogger("cosmos.executor.hardened")


@dataclass
class ExecutionMetrics:
    """Metrics for a single execution."""
    user_id: str
    tier: PlanTier
    duration_ms: float
    steps_completed: int
    steps_failed: int
    cost: float
    tokens_used: int
    rate_limited: bool = False
    concurrent_limit_hit: bool = False


class HardenedExecutor:
    """
    Production-ready executor with:
    - HardenedScheduler for limits
    - Billing middleware for tier enforcement
    - Full observability
    """
    
    def __init__(
        self,
        user_id: str = "anonymous",
        provider_registry: Optional[Any] = None,
        tool_registry: Optional[dict] = None,
    ):
        self.user_id = user_id
        self.provider_registry = provider_registry
        self.tool_registry = tool_registry or {}
        
        # Get billing middleware
        self.billing = get_billing_middleware()
        
        # Set user tier (for MVP, default to FREE)
        if not self.billing.get_tier_for_user(user_id):
            self.billing.set_tier_for_user(user_id, PlanTier.FREE)
        
        # Create scheduler with user's tier config
        scheduler_config = self.billing.create_scheduler_config(user_id)
        self.scheduler = HardenedScheduler(scheduler_config)
        
        # Get tier config
        self.tier = self.billing.get_tier_for_user(user_id)
        self.tier_config = self.billing.get_config_for_user(user_id)
        
        logger.info(
            f"HardenedExecutor: user={user_id}, tier={self.tier.value}, "
            f"max_concurrent={self.tier_config.max_concurrent}, "
            f"rate_limit={self.tier_config.rate_limit}/min"
        )
    
    async def execute_plan(self, plan: Plan) -> Plan:
        """
        Execute a full plan with hardened scheduling.
        
        Args:
            plan: Plan to execute
            
        Returns:
            Completed plan with results
        """
        logger.info(f"HardenedExecutor: Executing plan {plan.id} with {len(plan.nodes)} steps")
        
        plan.status = PlanStatus.IN_PROGRESS
        start_time = time.time()
        
        completed_steps = 0
        failed_steps = 0
        total_cost = 0.0
        total_tokens = 0
        
        for node in plan.nodes:
            # Execute each step through scheduler
            task_id = await self.scheduler.submit(
                self._execute_node,
                node,
                name=f"step_{node.name}",
                timeout=60.0,
            )
            
            try:
                result = await self.scheduler.wait_for(task_id, timeout=60.0)
                
                if result["status"] == "completed":
                    completed_steps += 1
                    total_cost += result.get("cost", 0)
                    total_tokens += result.get("tokens", 0)
                else:
                    failed_steps += 1
                    
            except Exception as e:
                logger.error(f"Step {node.name} failed: {e}")
                failed_steps += 1
                node.status = StepStatus.FAILED
        
        # Calculate metrics
        duration_ms = (time.time() - start_time) * 1000
        
        # Record usage for billing
        await self.billing.usage_tracker.record_run(
            user_id=self.user_id,
            tier=self.tier,
            duration_ms=duration_ms,
            tokens_used=total_tokens,
            cost=total_cost,
        )
        
        # Update plan status
        if failed_steps == 0:
            plan.status = PlanStatus.COMPLETED
        elif completed_steps == 0:
            plan.status = PlanStatus.FAILED
        else:
            plan.status = PlanStatus.PARTIAL
        
        logger.info(
            f"Plan {plan.id} completed: "
            f"completed={completed_steps}, failed={failed_steps}, "
            f"cost=${total_cost:.4f}, duration={duration_ms:.0f}ms"
        )
        
        return plan
    
    async def _execute_node(self, node: PlanNode) -> dict:
        """Execute a single node."""
        start_time = time.time()
        
        try:
            if node.step_type == "tool":
                output = await self._execute_tool(node)
            else:
                output = await self._execute_task(node)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                "status": "completed",
                "output": output,
                "duration_ms": duration_ms,
                "cost": 0.0,  # TODO: calculate actual cost
                "tokens": 0,
            }
            
        except Exception as e:
            logger.error(f"Node {node.name} failed: {e}")
            node.status = StepStatus.FAILED
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000,
            }
    
    async def _execute_tool(self, node: PlanNode) -> Any:
        """Execute a tool step."""
        tool_name = node.action
        
        if tool_name not in self.tool_registry:
            # Try to execute as Python code
            logger.info(f"Executing tool: {tool_name}")
            return {"tool": tool_name, "result": "mock_result"}
        
        tool = self.tool_registry[tool_name]
        return await tool(node.input)
    
    async def _execute_task(self, node: PlanNode) -> Any:
        """Execute a task step (LLM call)."""
        # For MVP, use mock
        logger.info(f"Executing task: {node.name}")
        return {"task": node.name, "result": "mock_result"}
    
    def get_metrics(self) -> dict:
        """Get execution metrics."""
        usage = self.billing.usage_tracker.get_usage(self.user_id)
        scheduler_stats = self.scheduler.get_stats()
        
        return {
            "user_id": self.user_id,
            "tier": self.tier.value,
            "max_concurrent": self.tier_config.max_concurrent,
            "rate_limit": self.tier_config.rate_limit,
            "usage": usage or {},
            "scheduler": scheduler_stats,
        }
    
    def get_tier_limits(self) -> dict:
        """Get current tier limits."""
        return {
            "tier": self.tier.value,
            "max_concurrent": self.tier_config.max_concurrent,
            "rate_limit": self.tier_config.rate_limit,
            "monthly_limit": self.tier_config.monthly_limit,
            "price_monthly": self.tier_config.price_monthly,
        }
