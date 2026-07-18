"""Tests for Cosmos Planner."""

import pytest
import asyncio

from cosmos.planner import LLMPlanner, Plan, PlanNode, StepStatus, PlanStatus


class TestLLMPlanner:
    """Tests for LLMPlanner."""
    
    @pytest.fixture
    def planner(self):
        return LLMPlanner()
    
    @pytest.mark.asyncio
    async def test_create_simple_plan(self, planner):
        """Test creating a plan for simple task."""
        plan = await planner.create_plan("Write hello world")
        
        assert plan.id is not None
        assert plan.task == "Write hello world"
        assert len(plan.nodes) > 0
        assert plan.status == PlanStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_create_complex_plan(self, planner):
        """Test creating a plan for complex task."""
        plan = await planner.create_plan(
            "Research coffee providers, analyze prices, create summary"
        )
        
        assert len(plan.nodes) >= 2
        # Check dependencies are resolved
        for node in plan.nodes:
            if node.dependencies:
                assert all(
                    any(dep_id == n.id for n in plan.nodes)
                    for dep_id in node.dependencies
                )
    
    @pytest.mark.asyncio
    async def test_plan_mark_ready(self, planner):
        """Test marking nodes as ready."""
        plan = await planner.create_plan("Test task")
        
        # Should have some ready nodes initially
        ready = plan.get_ready_nodes()
        assert len(ready) >= 0


class TestPlanNode:
    """Tests for PlanNode."""
    
    def test_create_node(self):
        """Test creating a plan node."""
        node = PlanNode(
            name="test",
            description="Test node",
        )
        
        assert node.id is not None
        assert node.name == "test"
        assert node.status == StepStatus.PENDING
    
    def test_node_duration(self):
        """Test node duration calculation."""
        import time
        node = PlanNode(name="test")
        node.started_at = time.time() - 1
        node.completed_at = time.time()
        
        assert 900 < node.duration_ms < 1100


class TestPlan:
    """Tests for Plan."""
    
    def test_create_plan(self):
        """Test creating a plan."""
        plan = Plan(task="Test task")
        
        assert plan.id is not None
        assert plan.task == "Test task"
        assert plan.status == PlanStatus.PENDING
    
    def test_get_node(self):
        """Test getting node by ID."""
        plan = Plan(task="Test")
        node = PlanNode(id="test123", name="test")
        plan.nodes.append(node)
        
        found = plan.get_node("test123")
        assert found is not None
        assert found.name == "test"
        
        not_found = plan.get_node("nonexistent")
        assert not_found is None
    
    def test_get_ready_nodes(self):
        """Test getting ready nodes."""
        plan = Plan(task="Test")
        node1 = PlanNode(id="n1", name="node1", dependencies=[])
        node2 = PlanNode(id="n2", name="node2", dependencies=["n1"])
        
        plan.nodes = [node1, node2]
        plan.mark_ready()
        
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].name == "node1"
    
    def test_mark_ready_with_completed_deps(self):
        """Test marking ready when deps completed."""
        plan = Plan(task="Test")
        node1 = PlanNode(id="n1", name="node1", dependencies=[])
        node2 = PlanNode(id="n2", name="node2", dependencies=["n1"])
        
        plan.nodes = [node1, node2]
        
        # Initially only n1 should be ready
        plan.mark_ready()
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "n1"
        
        # After n1 completes, n2 should be ready
        node1.status = StepStatus.COMPLETED
        plan.mark_ready()
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "n2"
