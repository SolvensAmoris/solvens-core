"""Tests for Cosmos Scheduler."""

import pytest
import asyncio

from cosmos.scheduler import DAGScheduler, ScheduleDecision
from cosmos.planner import Plan, PlanNode, StepStatus, PlanStatus


class TestDAGScheduler:
    """Tests for DAGScheduler."""
    
    @pytest.fixture
    def scheduler(self):
        return DAGScheduler(max_concurrent=3)
    
    @pytest.mark.asyncio
    async def test_simple_schedule(self, scheduler):
        """Test scheduling a simple plan."""
        plan = Plan(task="Simple task")
        plan.nodes = [
            PlanNode(id="n1", name="step1", dependencies=[]),
        ]
        
        result = await scheduler.schedule(plan)
        
        assert result.status == PlanStatus.COMPLETED
        assert result.nodes[0].status == StepStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, scheduler):
        """Test parallel execution of independent nodes."""
        plan = Plan(task="Parallel task")
        plan.nodes = [
            PlanNode(id="n1", name="step1", dependencies=[]),
            PlanNode(id="n2", name="step2", dependencies=[]),
            PlanNode(id="n3", name="step3", dependencies=[]),
        ]
        
        result = await scheduler.schedule(plan)
        
        assert result.status == PlanStatus.COMPLETED
        assert all(n.status == StepStatus.COMPLETED for n in result.nodes)
    
    @pytest.mark.asyncio
    async def test_sequential_execution(self, scheduler):
        """Test sequential execution with dependencies."""
        plan = Plan(task="Sequential task")
        plan.nodes = [
            PlanNode(id="n1", name="step1", dependencies=[]),
            PlanNode(id="n2", name="step2", dependencies=["n1"]),
            PlanNode(id="n3", name="step3", dependencies=["n2"]),
        ]
        
        result = await scheduler.schedule(plan)
        
        assert result.status == PlanStatus.COMPLETED
        # Check execution order via events
        events = scheduler.get_events()
        step_events = [e for e in events if e.action == "complete"]
        assert len(step_events) == 3
    
    @pytest.mark.asyncio
    async def test_diamond_dependency(self, scheduler):
        """Test diamond-shaped dependency graph."""
        plan = Plan(task="Diamond task")
        plan.nodes = [
            PlanNode(id="a", name="start", dependencies=[]),
            PlanNode(id="b", name="b1", dependencies=["a"]),
            PlanNode(id="c", name="c1", dependencies=["a"]),
            PlanNode(id="d", name="end", dependencies=["b", "c"]),
        ]
        
        result = await scheduler.schedule(plan)
        
        assert result.status == PlanStatus.COMPLETED
        assert all(n.status == StepStatus.COMPLETED for n in result.nodes)
    
    def test_schedule_decision(self):
        """Test ScheduleDecision creation."""
        decision = ScheduleDecision(
            node_id="test",
            action="execute",
            reason="Test reason"
        )
        
        assert decision.node_id == "test"
        assert decision.action == "execute"
        assert decision.reason == "Test reason"
        assert decision.scheduled_at > 0
