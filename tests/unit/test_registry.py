"""Tests for plugin system."""

import pytest
from pathlib import Path

from solvens.core.exceptions import PluginError, PluginNotFoundError
from solvens.registry.manager import PluginManager, PluginMetadata, Plugin


class TestPluginMetadata:
    """Tests for PluginMetadata."""

    def test_create_metadata(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            entry_point="test.plugin",
        )
        
        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.entry_point == "test.plugin"

    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = PluginMetadata(
            name="test",
            entry_point="test",
        )
        
        assert metadata.version == "0.1.0"
        assert metadata.description == ""
        assert metadata.dependencies == []


class TestPluginManager:
    """Tests for PluginManager."""

    def test_create_manager(self):
        """Test creating a plugin manager."""
        manager = PluginManager()
        assert manager.plugins_dir is not None
        assert len(manager.list_plugins()) == 0

    def test_register_plugin(self):
        """Test registering a plugin."""
        manager = PluginManager()
        metadata = PluginMetadata(
            name="test",
            entry_point="test",
        )
        
        manager.register_plugin(metadata)
        
        assert "test" in manager.list_plugins()

    def test_register_duplicate(self):
        """Test that registering duplicate plugins raises error."""
        manager = PluginManager()
        metadata = PluginMetadata(
            name="test",
            entry_point="test",
        )
        
        manager.register_plugin(metadata)
        
        with pytest.raises(PluginError):
            manager.register_plugin(metadata)

    def test_get_plugin_not_found(self):
        """Test that getting non-existent plugin raises error."""
        manager = PluginManager()
        
        with pytest.raises(PluginNotFoundError):
            manager.get_plugin("nonexistent")

    def test_stats(self):
        """Test getting plugin statistics."""
        manager = PluginManager()
        metadata = PluginMetadata(
            name="test",
            entry_point="test",
        )
        manager.register_plugin(metadata)
        
        stats = manager.stats
        
        assert stats["total_registered"] == 1
        assert stats["total_loaded"] == 0
        assert stats["loaded_plugins"] == []
