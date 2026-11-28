"""Base classes for SOLVENS CORE.

Provides fundamental abstractions that all modules extend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel as PydanticBaseModel

T = TypeVar("T")


class BaseModel(PydanticBaseModel):
    """Base model extending Pydantic's BaseModel.
    
    All data models in SOLVENS CORE inherit from this class.
    Provides automatic validation and serialization.
    """

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "frozen": False,
    }


class BaseService(ABC, Generic[T]):
    """Base service class for all services.
    
    Provides lifecycle management and dependency injection patterns.
    
    Type Parameters:
        T: The type of managed resource
    """

    def __init__(self) -> None:
        self._initialized = False
        self._resource: T | None = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service. Called once at startup."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service. Called once at shutdown."""
        ...

    async def start(self) -> T:
        """Start the service and return the managed resource."""
        if not self._initialized:
            await self.initialize()
            self._initialized = True
        return self.get_resource()

    async def stop(self) -> None:
        """Stop the service gracefully."""
        if self._initialized:
            await self.shutdown()
            self._initialized = False

    def get_resource(self) -> T:
        """Get the managed resource."""
        if self._resource is None:
            raise RuntimeError("Service not started")
        return self._resource

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized


class BasePlugin(ABC):
    """Base class for all plugins.
    
    Plugins extend SOLVENS CORE without modifying core code.
    """

    name: str
    version: str

    @abstractmethod
    async def load(self) -> None:
        """Load the plugin and register its capabilities."""
        ...

    @abstractmethod
    async def unload(self) -> None:
        """Unload the plugin and cleanup resources."""
        ...

    @property
    @abstractmethod
    def dependencies(self) -> list[str]:
        """List of plugin names this plugin depends on."""
        ...
