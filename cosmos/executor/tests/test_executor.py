"""Tests for Cosmos Executor."""

import pytest
import asyncio

from cosmos.executor import StepExecutor, StepResult, ToolRegistry
from cosmos.planner import PlanNode, StepStatus


class TestStepExecutor:
    """Tests for StepExecutor."""
    
    @pytest.fixture
    def executor(self):
        return StepExecutor()
    
    @pytest.mark.asyncio
    async def test_execute_task_step(self, executor):
        """Test executing a task step."""
        node = PlanNode(
            name="test_task",
            description="Test task",
            step_type="task",
        )
        
        result = await executor.execute(node)
        
        assert result.step_id == node.id
        assert result.status == StepStatus.COMPLETED
        assert result.output is not None
        assert result.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_execute_tool_step(self, executor):
        """Test executing a tool step."""
        node = PlanNode(
            name="test_tool",
            description="Test tool",
            step_type="tool",
            tools=["test_tool"],
        )
        
        result = await executor.execute(node)
        
        assert result.step_id == node.id
        assert result.status == StepStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_error_handling(self, executor):
        """Test error handling."""
        node = PlanNode(
            name="test_error",
            description="Test error",
            step_type="invalid_type",
        )
        
        # This should not raise, just return failed status
        result = await executor.execute(node)
        
        # The mock executor handles errors gracefully
        assert result.step_id == node.id


class TestToolRegistry:
    """Tests for ToolRegistry."""
    
    @pytest.fixture
    def registry(self):
        return ToolRegistry()
    
    def test_register_tool(self, registry):
        """Test registering a tool."""
        def my_tool(inputs):
            return "result"
        
        registry.register("my_tool", my_tool)
        
        assert "my_tool" in registry.list_tools()
    
    def test_get_tool(self, registry):
        """Test getting a tool."""
        def my_tool(inputs):
            return "result"
        
        registry.register("my_tool", my_tool)
        tool = registry.get("my_tool")
        
        assert tool is not None
    
    def test_get_nonexistent_tool(self, registry):
        """Test getting nonexistent tool returns None."""
        tool = registry.get("nonexistent")
        assert tool is None
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, registry):
        """Test executing a registered tool."""
        async def my_tool(inputs):
            return f"Processed: {inputs.get('value', '')}"
        
        registry.register("async_tool", my_tool)
        result = await registry.execute("async_tool", {"value": "test"})
        
        assert result == "Processed: test"
    
    def test_list_tools(self, registry):
        """Test listing tools."""
        def tool1(inputs): return "t1"
        def tool2(inputs): return "t2"
        
        registry.register("tool1", tool1)
        registry.register("tool2", tool2)
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools


class TestStepResult:
    """Tests for StepResult."""
    
    def test_create_success_result(self):
        """Test creating a successful result."""
        result = StepResult(
            step_id="test",
            status=StepStatus.COMPLETED,
            output="success",
            duration_ms=100.0,
        )
        
        assert result.step_id == "test"
        assert result.status == StepStatus.COMPLETED
        assert result.output == "success"
        assert result.duration_ms == 100.0
    
    def test_create_error_result(self):
        """Test creating an error result."""
        result = StepResult(
            step_id="test",
            status=StepStatus.FAILED,
            error="Something went wrong",
            duration_ms=50.0,
        )
        
        assert result.step_id == "test"
        assert result.status == StepStatus.FAILED
        assert result.error == "Something went wrong"
