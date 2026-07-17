"""Tests for core module."""

import pytest
from datetime import datetime

from solvens.core.types import (
    Message,
    MessageRole,
    Task,
    TaskPriority,
    TaskStatus,
    Model,
    Provider,
    ProviderType,
    ModelCapability,
)
from solvens.core.base import BaseModel


class TestMessage:
    """Tests for Message model."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.name is None

    def test_message_with_name(self):
        """Test message with name."""
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Hello!",
            name="assistant"
        )
        assert msg.name == "assistant"

    def test_message_default_timestamp(self):
        """Test message has default timestamp."""
        msg = Message(role=MessageRole.USER, content="Test")
        assert msg.created_at is not None
        assert isinstance(msg.created_at, datetime)


class TestTask:
    """Tests for Task model."""

    def test_create_task(self):
        """Test creating a task."""
        task = Task(
            id="test-1",
            description="Test task"
        )
        assert task.id == "test-1"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL

    def test_task_lifecycle(self):
        """Test task status transitions."""
        task = Task(id="test-1", description="Test")
        
        # Start task
        task.start()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        
        # Complete task
        task.complete(result="success")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "success"
        assert task.completed_at is not None

    def test_task_fail(self):
        """Test task failure."""
        task = Task(id="test-1", description="Test")
        task.start()
        task.fail("Error occurred")
        
        assert task.status == TaskStatus.FAILED
        assert task.error == "Error occurred"

    def test_task_cancel(self):
        """Test task cancellation."""
        task = Task(id="test-1", description="Test")
        task.cancel()
        assert task.status == TaskStatus.CANCELLED


class TestProvider:
    """Tests for Provider model."""

    def test_create_provider(self):
        """Test creating a provider."""
        provider = Provider(
            name="OpenAI",
            type=ProviderType.OPENAI,
            enabled=True
        )
        assert provider.name == "OpenAI"
        assert provider.type == ProviderType.OPENAI
        assert provider.enabled is True

    def test_provider_with_models(self):
        """Test provider with models."""
        model = Model(
            id="gpt-4",
            name="GPT-4",
            provider=ProviderType.OPENAI,
            capabilities=[ModelCapability.CHAT]
        )
        provider = Provider(
            name="OpenAI",
            type=ProviderType.OPENAI,
            models=[model]
        )
        assert len(provider.models) == 1
        assert provider.models[0].id == "gpt-4"


class TestModel:
    """Tests for Model configuration."""

    def test_create_model(self):
        """Test creating a model."""
        model = Model(
            id="gpt-4",
            name="GPT-4",
            provider=ProviderType.OPENAI,
            capabilities=[ModelCapability.CHAT, ModelCapability.EMBEDDINGS]
        )
        assert model.id == "gpt-4"
        assert ModelCapability.CHAT in model.capabilities

    def test_model_defaults(self):
        """Test model default values."""
        model = Model(
            id="test",
            name="Test",
            provider=ProviderType.OLLAMA
        )
        assert model.max_tokens == 4096
        assert model.context_window == 128000


class TestRoutingRules:
    """Tests for routing rules."""

    def test_code_pattern_matching(self):
        """Test code pattern detection."""
        from solvens.router.rules import DefaultRoutingRules
        
        rules = DefaultRoutingRules.get_default_rules()
        code_rule = next(r for r in rules if r.name == "code_generation")
        
        # Should match Python code
        assert code_rule.matches("def hello(): return 'world'")
        assert code_rule.matches("function test() { }")
        assert code_rule.matches("class MyClass: pass")
        
        # Should not match regular text
        assert not code_rule.matches("What's the weather like?")

    def test_research_pattern_matching(self):
        """Test research pattern detection."""
        from solvens.router.rules import DefaultRoutingRules
        
        rules = DefaultRoutingRules.get_default_rules()
        research_rule = next(r for r in rules if r.name == "research")
        
        assert research_rule.matches("Analyze the data")
        assert research_rule.matches("Research on AI trends")
        
    def test_offline_pattern_matching(self):
        """Test offline pattern detection."""
        from solvens.router.rules import DefaultRoutingRules
        
        rules = DefaultRoutingRules.get_offline_rules()
        offline_rule = rules[0]
        
        assert offline_rule.matches("offline mode")
        assert offline_rule.matches("local server")
        assert offline_rule.matches("no internet available")
        assert offline_rule.provider == ProviderType.OLLAMA
