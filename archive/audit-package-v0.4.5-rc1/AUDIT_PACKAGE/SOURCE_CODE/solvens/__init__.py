"""SOLVENS CORE - AI Operating System Kernel

SOLVENS CORE is the modular kernel that powers all applications in the Solvens ecosystem.
It provides a foundation for building intelligent agents with multi-provider support,
event-driven architecture, and plugin extensibility.
"""

__version__ = "0.1.0"
__author__ = "Luis Alberto Burciaga Miker"

from solvens.core.base import BaseModel, BaseService
from solvens.core.config import Settings, get_settings
from solvens.core.types import (
    Message,
    MessageRole,
    Model,
    Provider,
    Task,
    TaskPriority,
    TaskStatus,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "BaseModel",
    "BaseService",
    "Settings",
    "get_settings",
    # Types
    "Message",
    "MessageRole",
    "Model",
    "Provider",
    "Task",
    "TaskPriority",
    "TaskStatus",
]
