"""Plugin Registry for SOLVENS CORE.

Manages dynamic plugin loading and lifecycle.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from pydantic import Field

from solvens.core.base import BaseModel
from solvens.core.exceptions import PluginError, PluginLoadError, PluginNotFoundError

logger = structlog.get_logger(__name__)


class PluginMetadata(BaseModel):
    """Metadata for a registered plugin.
    
    Attributes:
        name: Plugin name (unique identifier)
        version: Plugin version
        description: Plugin description
        author: Plugin author
        entry_point: Module or class to load
        dependencies: Other plugins this depends on
        config: Plugin-specific configuration
    """
    
    model_config = {"extra": "ignore"}
    
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    entry_point: str
    dependencies: list[str] = []
    config: dict[str, Any] = {}


class Plugin(ABC):
    """Base class for all plugins.
    
    Plugins extend SOLVENS CORE functionality without modifying core code.
    """
    
    metadata: PluginMetadata
    
    @abstractmethod
    async def load(self) -> None:
        """Load and initialize the plugin."""
        ...
    
    @abstractmethod
    async def unload(self) -> None:
        """Unload and cleanup the plugin."""
        ...
    
    @abstractmethod
    def get_services(self) -> dict[str, Any]:
        """Return services provided by this plugin."""
        ...


class PluginManager:
    """Manages plugin loading, lifecycle, and dependencies.
    
    Features:
    - Dynamic plugin discovery
    - Dependency resolution
    - Lifecycle management
    - Configuration injection
    """
    
    def __init__(self, plugins_dir: Path | None = None):
        self.plugins_dir = plugins_dir or Path(__file__).parent.parent / "plugins"
        self._plugins: dict[str, Plugin] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._instances: dict[str, Any] = {}
    
    def discover_plugins(self) -> list[PluginMetadata]:
        """Discover available plugins in the plugins directory."""
        discovered = []
        
        if not self.plugins_dir.exists():
            logger.warning("Plugins directory not found", path=str(self.plugins_dir))
            return discovered
        
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                metadata = self._load_plugin_metadata(item)
                if metadata:
                    discovered.append(metadata)
                    logger.info("Plugin discovered", name=metadata.name, version=metadata.version)
        
        return discovered
    
    def _load_plugin_metadata(self, plugin_path: Path) -> PluginMetadata | None:
        """Load plugin metadata from __init__.py or config file."""
        try:
            # Try to import and get metadata
            module_name = f"solvens.plugins.{plugin_path.name}"
            spec = importlib.util.find_spec(module_name)
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Check for PLUGIN_METADATA
                if hasattr(module, "PLUGIN_METADATA"):
                    return PluginMetadata(**module.PLUGIN_METADATA)
                
                # Create metadata from module
                return PluginMetadata(
                    name=plugin_path.name,
                    version=getattr(module, "__version__", "0.1.0"),
                    description=getattr(module, "__doc__", "") or "",
                    entry_point=module_name,
                )
        except Exception as e:
            logger.error("Failed to load plugin metadata", path=str(plugin_path), error=str(e))
        
        return None
    
    def register_plugin(self, metadata: PluginMetadata) -> None:
        """Register a plugin with its metadata."""
        if metadata.name in self._metadata:
            raise PluginLoadError(f"Plugin {metadata.name} already registered")
        
        self._metadata[metadata.name] = metadata
        logger.info("Plugin registered", name=metadata.name, version=metadata.version)
    
    async def load_plugin(self, name: str, **config: Any) -> Any:
        """Load and initialize a plugin.
        
        Args:
            name: Plugin name
            **config: Configuration to pass to plugin
            
        Returns:
            Plugin instance
            
        Raises:
            PluginNotFoundError: If plugin not found
            PluginLoadError: If plugin fails to load
        """
        if name in self._instances:
            return self._instances[name]
        
        metadata = self._metadata.get(name)
        if not metadata:
            raise PluginNotFoundError(f"Plugin {name} not found")
        
        # Check dependencies
        for dep in metadata.dependencies:
            if dep not in self._instances:
                await self.load_plugin(dep)
        
        try:
            # Import the plugin module
            module = importlib.import_module(metadata.entry_point)
            
            # Create plugin instance
            if hasattr(module, "create_plugin"):
                instance = module.create_plugin(config)
            else:
                instance = module
            
            # Initialize plugin
            if hasattr(instance, "load"):
                await instance.load()
            
            self._instances[name] = instance
            self._plugins[name] = instance
            
            logger.info("Plugin loaded successfully", name=name)
            return instance
            
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin {name}: {e}") from e
    
    async def unload_plugin(self, name: str) -> None:
        """Unload a plugin.
        
        Args:
            name: Plugin name
            
        Raises:
            PluginNotFoundError: If plugin not loaded
        """
        if name not in self._instances:
            raise PluginNotFoundError(f"Plugin {name} not loaded")
        
        instance = self._instances[name]
        
        try:
            if hasattr(instance, "unload"):
                await instance.unload()
            
            del self._instances[name]
            del self._plugins[name]
            
            logger.info("Plugin unloaded", name=name)
            
        except Exception as e:
            raise PluginError(f"Failed to unload plugin {name}: {e}") from e
    
    def get_plugin(self, name: str) -> Any:
        """Get a loaded plugin instance.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance
            
        Raises:
            PluginNotFoundError: If plugin not loaded
        """
        if name not in self._instances:
            raise PluginNotFoundError(f"Plugin {name} not loaded")
        return self._instances[name]
    
    def list_plugins(self) -> list[str]:
        """List all registered plugin names."""
        return list(self._metadata.keys())
    
    def list_loaded_plugins(self) -> list[str]:
        """List all currently loaded plugin names."""
        return list(self._instances.keys())
    
    async def reload_plugin(self, name: str) -> Any:
        """Reload a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            New plugin instance
        """
        await self.unload_plugin(name)
        return await self.load_plugin(name)
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get plugin statistics."""
        return {
            "total_registered": len(self._metadata),
            "total_loaded": len(self._instances),
            "loaded_plugins": list(self._instances.keys()),
        }
