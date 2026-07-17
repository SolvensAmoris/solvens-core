"""Tests for Agent Orchestrator."""

import pytest
import asyncio

from solvens.agents.orchestrator import AgentOrchestrator, OrchestratorConfig, TaskResult
from solvens.core.types import TaskPriority, TaskStatus


@pytest.fixture
async def orchestrator():
    """Create and initialize an orchestrator."""
    config = OrchestratorConfig(
        max_concurrent_tasks=5,
        task_timeout=10,
        max_retries=2,
    )
    orch = AgentOrchestrator(config)
    await orch.initialize()
    yield orch
    await orch.shutdown()


@pytest.fixture
def sample_task():
    """Sample async task function."""
    async def task():
        await asyncio.sleep(0.01)
        return "task result"
    return task


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestratorConfig()
        assert config.max_concurrent_tasks == 10
        assert config.task_timeout == 300
        assert config.max_retries == 3
        assert config.queue_size == 1000

    def test_custom_config(self):
        """Test custom configuration."""
        config = OrchestratorConfig(
            max_concurrent_tasks=20,
            task_timeout=60,
        )
        assert config.max_concurrent_tasks == 20
        assert config.task_timeout == 60


class TestTaskLifecycle:
    """Tests for task lifecycle management."""

    @pytest.mark.asyncio
    async def test_create_task(self, orchestrator, sample_task):
        """Test creating a task."""
        task = orchestrator.create_task(
            description="Test task",
            callback=sample_task,
            priority=TaskPriority.HIGH
        )
        
        assert task.id is not None
        assert task.description == "Test task"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_submit_task(self, orchestrator, sample_task):
        """Test submitting a task."""
        task_id = await orchestrator.submit_task(
            description="Submit test",
            callback=sample_task,
            priority=TaskPriority.NORMAL
        )
        
        assert task_id is not None
        assert len(task_id) > 0

    @pytest.mark.asyncio
    async def test_execute_task(self, orchestrator):
        """Test direct task execution."""
        async def quick_task():
            await asyncio.sleep(0.01)
            return "quick result"
        
        result = await orchestrator.execute_task(
            description="Execute test",
            callback=quick_task,
            timeout=5
        )
        
        assert isinstance(result, TaskResult)
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "quick result"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_task_failure(self, orchestrator):
        """Test task failure handling."""
        async def failing_task():
            raise ValueError("Task failed intentionally")
        
        result = await orchestrator.execute_task(
            description="Failing task",
            callback=failing_task
        )
        
        assert result.status == TaskStatus.FAILED
        assert "Task failed intentionally" in result.error

    @pytest.mark.asyncio
    async def test_get_task(self, orchestrator, sample_task):
        """Test getting a task by ID."""
        task_id = await orchestrator.submit_task(
            description="Get test",
            callback=sample_task
        )
        
        task = orchestrator.get_task(task_id)
        assert task.id == task_id

    @pytest.mark.asyncio
    async def test_cancel_task(self, orchestrator, sample_task):
        """Test task cancellation."""
        # Create a long-running task
        async def long_task():
            await asyncio.sleep(10)
            return "done"
        
        task_id = await orchestrator.submit_task(
            description="Long task",
            callback=long_task
        )
        
        # Cancel it
        cancelled = await orchestrator.cancel_task(task_id)
        assert cancelled is True
        
        task = orchestrator.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED


class TestTaskQueue:
    """Tests for task queuing."""

    @pytest.mark.asyncio
    async def test_priority_ordering(self, orchestrator):
        """Test that higher priority tasks run first."""
        execution_order = []
        
        async def make_task(task_num: int):
            async def task():
                execution_order.append(task_num)
                await asyncio.sleep(0.05)
            return task
        
        # Submit tasks in reverse priority order
        await orchestrator.submit_task(
            description="Task 1 (LOW)",
            callback=await make_task(1),
            priority=TaskPriority.LOW
        )
        await orchestrator.submit_task(
            description="Task 2 (HIGH)",
            callback=await make_task(2),
            priority=TaskPriority.HIGH
        )
        
        # Wait for execution
        await asyncio.sleep(0.3)
        
        # High priority should execute first
        assert execution_order.index(2) < execution_order.index(1)


class TestEventSystem:
    """Tests for event hooks."""

    @pytest.mark.asyncio
    async def test_event_hook(self, orchestrator, sample_task):
        """Test registering and triggering event hooks."""
        events = []
        
        def on_start(task):
            events.append(f"start:{task.id}")
        
        orchestrator.on("task_start", on_start)
        
        await orchestrator.submit_task(
            description="Event test",
            callback=sample_task
        )
        
        # Wait for task to complete
        await asyncio.sleep(0.2)
        
        assert len(events) == 1
        assert events[0].startswith("start:")


class TestOrchestratorStats:
    """Tests for orchestrator statistics."""

    @pytest.mark.asyncio
    async def test_initial_stats(self, orchestrator):
        """Test initial statistics."""
        stats = orchestrator.stats
        
        assert "total_tasks" in stats
        assert "running_tasks" in stats
        assert "queued_tasks" in stats
        assert "workers" in stats
        assert stats["workers"] == 5  # From fixture

    @pytest.mark.asyncio
    async def test_stats_after_tasks(self, orchestrator):
        """Test statistics after running tasks."""
        async def quick_task():
            await asyncio.sleep(0.01)
            return "done"
        
        # Run a task
        await orchestrator.execute_task(
            description="Stats test",
            callback=quick_task
        )
        
        stats = orchestrator.stats
        assert stats["completed"] >= 1
