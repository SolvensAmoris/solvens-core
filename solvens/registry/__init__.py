"""Plugin registry for SOLVENS CORE.

Manages dynamic plugin loading and lifecycle.
"""

from solvens.registry.manager import Plugin, PluginManager, PluginMetadata

__all__ = [
    "Plugin",
    "PluginManager",
    "PluginMetadata",
]
