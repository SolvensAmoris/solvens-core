"""Tests for provider system."""

import pytest
from solvens.core.types import Message, MessageRole, ProviderType, Model, ModelCapability
from solvens.providers.base import ProviderClient, ChatOptions


class TestProviderInterface:
    """Tests for the provider interface."""

    def test_chat_options_defaults(self):
        """Test ChatOptions default values."""
        options = ChatOptions()
        assert options.temperature == 0.7
        assert options.max_tokens is None
        assert options.stream is False

    def test_chat_options_custom(self):
        """Test ChatOptions with custom values."""
        options = ChatOptions(
            temperature=0.9,
            max_tokens=1000,
            stream=True,
        )
        assert options.temperature == 0.9
        assert options.max_tokens == 1000
        assert options.stream is True

    def test_provider_client_abstract(self):
        """Test that ProviderClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ProviderClient()


class TestOpenAIClient:
    """Tests for OpenAI client."""

    def test_client_creation(self):
        """Test creating an OpenAI client."""
        from solvens.plugins.openai import OpenAIClient
        
        client = OpenAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.provider_type == ProviderType.OPENAI
        assert client.provider_name == "OpenAI"
        assert client.supports_function_calling is True

    def test_message_conversion(self):
        """Test message format conversion."""
        from solvens.plugins.openai import OpenAIClient
        
        client = OpenAIClient(api_key="test-key")
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful"),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        
        converted = client._convert_messages(messages)
        
        assert len(converted) == 2
        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are helpful"
        assert converted[1]["role"] == "user"
        assert converted[1]["content"] == "Hello"

    def test_available_models(self):
        """Test getting available models."""
        from solvens.plugins.openai import OpenAIClient
        
        client = OpenAIClient(api_key="test-key")
        models = client.get_available_models()
        
        assert len(models) == 4
        model_ids = [m.id for m in models]
        assert "gpt-4-turbo" in model_ids
        assert "gpt-3.5-turbo" in model_ids


class TestOllamaClient:
    """Tests for Ollama client."""

    def test_client_creation(self):
        """Test creating an Ollama client."""
        from solvens.plugins.ollama import OllamaClient
        
        client = OllamaClient(base_url="http://localhost:11434")
        assert client.base_url == "http://localhost:11434"
        assert client.provider_type == ProviderType.OLLAMA
        assert client.provider_name == "Ollama"
        assert client.supports_function_calling is False

    def test_message_conversion(self):
        """Test message format conversion for Ollama."""
        from solvens.plugins.ollama import OllamaClient
        
        client = OllamaClient()
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
        ]
        
        converted = client._convert_messages(messages)
        
        assert "user: Hello" in converted
        assert "assistant: Hi there" in converted

    def test_available_models(self):
        """Test getting available models."""
        from solvens.plugins.ollama import OllamaClient
        
        client = OllamaClient()
        models = client.get_available_models()
        
        assert len(models) == 4
        model_ids = [m.id for m in models]
        assert "llama3.2" in model_ids
        assert "codellama" in model_ids


class TestAnthropicClient:
    """Tests for Anthropic client."""

    def test_client_creation(self):
        """Test creating an Anthropic client."""
        from solvens.plugins.anthropic import AnthropicClient
        
        client = AnthropicClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.provider_type == ProviderType.ANTHROPIC
        assert client.provider_name == "Anthropic"
        assert client.supports_vision is True

    def test_message_conversion(self):
        """Test message format conversion for Anthropic."""
        from solvens.plugins.anthropic import AnthropicClient
        
        client = AnthropicClient(api_key="test-key")
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are Claude"),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        
        converted = client._convert_messages(messages)
        
        # System message should be filtered out
        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert converted[0]["content"] == "Hello"

    def test_available_models(self):
        """Test getting available models."""
        from solvens.plugins.anthropic import AnthropicClient
        from solvens.core.types import ModelCapability
        
        client = AnthropicClient(api_key="test-key")
        models = client.get_available_models()
        
        assert len(models) == 4
        model_ids = [m.id for m in models]
        assert "claude-3-5-sonnet-20241022" in model_ids
        assert any(ModelCapability.VISION in m.capabilities for m in models)
