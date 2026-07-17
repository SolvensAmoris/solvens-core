"""Core module - Base classes and abstractions for SOLVENS CORE."""

from solvens.core.base import BaseModel, BaseService
from solvens.core.config import Settings, get_settings
from solvens.core.exceptions import (
    SolvensError,
    ConfigurationError,
    ProviderError,
    TaskError,
)
from solvens.core.types import (
    Message,
    MessageRole,
    Model,
    ModelCapability,
    Provider,
    ProviderType,
    Task,
    TaskPriority,
    TaskStatus,
)

__all__ = [
    # Base
    "BaseModel",
    "BaseService",
    # Config
    "Settings",
    "get_settings",
    # Exceptions
    "SolvensError",
    "ConfigurationError",
    "ProviderError",
    "TaskError",
    # Types
    "Message",
    "MessageRole",
    "Model",
    "ModelCapability",
    "Provider",
    "ProviderType",
    "Task",
    "TaskPriority",
    "TaskStatus",
]
