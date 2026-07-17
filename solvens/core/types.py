"""Core type definitions for SOLVENS CORE.

Defines the fundamental types used throughout the system.
"""

from __future__ import annotations

from datetime import timezone, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from solvens.core.base import BaseModel


class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A message in a conversation.
    
    Attributes:
        role: The role of the message sender
        content: The text content of the message
        name: Optional name for the sender
        tool_calls: Optional tool calls made in this message
        tool_call_id: Optional ID of a tool call response
    """

    role: MessageRole
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolCall(BaseModel):
    """A tool call made during agent execution."""
    
    id: str
    name: str
    arguments: dict[str, Any]


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Status of a task in the system."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """A task to be executed by an agent.
    
    Attributes:
        id: Unique identifier for the task
        description: Human-readable description
        priority: Execution priority
        status: Current execution status
        result: Task result data
        error: Error message if failed
    """

    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, result: Any | None = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)


class ProviderType(str, Enum):
    """Type of AI provider."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    GROK = "grok"
    SAKANA = "sakana"
    POLLO_AI = "pollo_ai"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    """Capabilities that models can have."""
    
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    SPEECH = "speech"
    IMAGE = "image"
    VIDEO = "video"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"


class Model(BaseModel):
    """An AI model configuration.
    
    Attributes:
        id: Unique model identifier (e.g., "gpt-4", "claude-3-opus")
        name: Human-readable name
        provider: Provider type
        capabilities: List of supported capabilities
        max_tokens: Maximum tokens in a single request
        context_window: Maximum context window size
    """

    id: str
    name: str
    provider: ProviderType
    capabilities: list[ModelCapability] = Field(default_factory=list)
    max_tokens: int = 4096
    context_window: int = 128000
    metadata: dict[str, Any] = Field(default_factory=dict)


class Provider(BaseModel):
    """An AI provider configuration.
    
    Attributes:
        name: Provider name (e.g., "openai", "anthropic")
        type: Provider type enum
        api_key: API key (stored securely, not exposed)
        base_url: API endpoint base URL
        models: List of available models
        enabled: Whether provider is active
    """

    name: str
    type: ProviderType
    api_key: str | None = None
    base_url: str | None = None
    models: list[Model] = Field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class Response(BaseModel):
    """A response from an AI provider.
    
    Attributes:
        content: Text content of the response
        model: Model used for the response
        usage: Token usage information
        finish_reason: Reason for completion
    """

    content: str
    model: str
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    """Token usage statistics."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
