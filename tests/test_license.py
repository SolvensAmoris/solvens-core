"""
tests/test_license.py
=====================

Tests for License and Telemetry systems.

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from cosmos.license import LicenseManager
from cosmos.telemetry import Telemetry


# ============================================================
# LICENSE TESTS
# ============================================================

class TestLicenseManager:
    """Test LicenseManager functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def lm(self, temp_dir):
        """Create LicenseManager with temp directory."""
        return LicenseManager(license_dir=temp_dir)
    
    def test_free_tier(self, lm):
        """Test free tier returns correct features."""
        result = lm.check()
        
        assert result["tier"] == "free"
        assert result["valid"] is True
        assert "core" in result["features"]
        assert "lsp" in result["features"]
    
    def test_activate_valid_key(self, lm):
        """Test activation with valid key."""
        assert lm.activate("COSMOS-COMM-TEST123")
        
        result = lm.check()
        assert result["tier"] == "commercial"
        assert result["valid"] is True
        assert "sso" in result["features"]
        assert "audit" in result["features"]
    
    def test_activate_invalid_key(self, lm):
        """Test activation with invalid key format."""
        assert lm.activate("INVALID-KEY") is False
        
        result = lm.check()
        assert result["tier"] == "free"
    
    def test_deactivate(self, lm):
        """Test deactivation returns to free tier."""
        lm.activate("COSMOS-COMM-TEST")
        assert lm.check()["tier"] == "commercial"
        
        lm.deactivate()
        assert lm.check()["tier"] == "free"
    
    def test_has_feature_free(self, lm):
        """Test feature checking on free tier."""
        assert lm.has_feature("core") is True
        assert lm.has_feature("lsp") is True
        assert lm.has_feature("sso") is False
        assert lm.has_feature("audit") is False
    
    def test_has_feature_commercial(self, lm):
        """Test feature checking on commercial tier."""
        lm.activate("COSMOS-COMM-TEST")
        
        assert lm.has_feature("core") is True
        assert lm.has_feature("sso") is True
        assert lm.has_feature("audit") is True
        assert lm.has_feature("sla") is True
    
    def test_is_commercial(self, lm):
        """Test is_commercial method."""
        assert lm.is_commercial() is False
        
        lm.activate("COSMOS-COMM-TEST")
        assert lm.is_commercial() is True


# ============================================================
# TELEMETRY TESTS
# ============================================================

class TestTelemetry:
    """Test Telemetry functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def tm(self, temp_dir):
        """Create Telemetry with temp directory."""
        return Telemetry(telemetry_dir=temp_dir)
    
    def test_free_tier_telemetry(self, tm):
        """Test telemetry works on free tier."""
        assert tm.enabled is True
        assert tm.user_id is not None
        assert len(tm.user_id) == 16  # SHA256 first 16 chars
    
    def test_track_event(self, tm):
        """Test tracking an event."""
        tm.track("compile_success", files=1, duration_ms=8)
        
        metrics = tm.get_metrics()
        assert metrics["total_events"] >= 1
    
    def test_track_compile_success(self, tm):
        """Test tracking successful compilation."""
        tm.track("compile_success", files=1, duration_ms=8)
        
        metrics = tm.get_metrics()
        assert metrics["total_compiles"] >= 1
    
    def test_track_e401(self, tm):
        """Test tracking E401 error."""
        tm.track("compile_e401", files=1, duration_ms=12, error_code="E401")
        
        metrics = tm.get_metrics()
        assert metrics["total_e401"] >= 1
    
    def test_metrics_aggregation(self, tm):
        """Test metrics aggregation."""
        # Track multiple events
        tm.track("compile_success", files=1, duration_ms=8)
        tm.track("compile_success", files=1, duration_ms=10)
        tm.track("compile_e401", files=1, duration_ms=5, error_code="E401")
        tm.track("cache_hit", duration_ms=1)
        
        metrics = tm.get_metrics()
        
        assert metrics["total_compiles"] >= 2
        assert metrics["total_e401"] >= 1
        assert metrics["unique_users"] == 1
        assert metrics["avg_compile_ms"] > 0
    
    def test_disable_telemetry(self, tm):
        """Test disabling telemetry."""
        tm.disable()
        assert tm.enabled is False
        
        # Should not track when disabled
        tm.track("compile_success", files=1)
        
        tm.enable()
        assert tm.enabled is True
    
    def test_clear_telemetry(self, tm):
        """Test clearing telemetry data."""
        tm.track("compile_success", files=1)
        assert tm.get_metrics()["total_events"] >= 1
        
        tm.clear()
        metrics = tm.get_metrics()
        assert metrics["total_events"] == 0
        assert metrics["total_compiles"] == 0
    
    def test_user_id_persistence(self, tm):
        """Test user ID is consistent across instances."""
        tm.track("event1")
        
        # Create new instance with same directory
        tm2 = Telemetry(telemetry_dir=tm.telemetry_dir)
        
        assert tm.user_id == tm2.user_id
    
    def test_telemetry_env_var(self, temp_dir, monkeypatch):
        """Test COSMOS_TELEMETRY environment variable."""
        monkeypatch.setenv("COSMOS_TELEMETRY", "0")
        
        tm = Telemetry(telemetry_dir=temp_dir)
        assert tm.enabled is False
    
    def test_empty_metrics(self, tm):
        """Test empty metrics returns defaults."""
        tm.clear()
        
        metrics = tm.get_metrics()
        
        assert metrics["total_compiles"] == 0
        assert metrics["total_e401"] == 0
        assert metrics["cache_hit_rate"] == 0.0
        assert metrics["unique_users"] == 1


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestLicenseTelemetryIntegration:
    """Test integration between license and telemetry."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_telemetry_works_on_free_tier(self, temp_dir):
        """Test telemetry works regardless of license tier."""
        lm = LicenseManager(license_dir=temp_dir)
        tm = Telemetry(telemetry_dir=temp_dir / "telemetry")
        
        # Free tier
        assert lm.check()["tier"] == "free"
        tm.track("compile_success", files=1)
        
        # Should work
        metrics = tm.get_metrics()
        assert metrics["total_events"] >= 1
    
    def test_telemetry_works_on_commercial(self, temp_dir):
        """Test telemetry works on commercial tier."""
        lm = LicenseManager(license_dir=temp_dir)
        tm = Telemetry(telemetry_dir=temp_dir / "telemetry")
        
        # Activate commercial
        lm.activate("COSMOS-COMM-TEST")
        assert lm.check()["tier"] == "commercial"
        
        tm.track("compile_success", files=1)
        
        # Should work
        metrics = tm.get_metrics()
        assert metrics["total_events"] >= 1
