"""
cosmos/telemetry.py
==================

Anonymous Telemetry for Cosmos Compiler
=======================================

Tracks:
- Compilation counts
- E401 errors
- Cache hits
- Unique users

Privacy:
- Anonymous (hash of hostname + username)
- Opt-out: COSMOS_TELEMETRY=0
- Local only (no external calls in this version)

Usage:
    from cosmos.telemetry import Telemetry, get_telemetry
    
    tm = Telemetry()
    tm.track("compile_success", files=1, duration_ms=8)
    
    # Get metrics
    metrics = tm.get_metrics()
    print(metrics["total_compiles"])

Autor: Luis Alberto Burciaga Miker
Version: 0.4.5-rc1
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class Telemetry:
    """
    Anonymous telemetry collector.
    
    Tracks usage metrics while respecting privacy:
    - User ID is anonymous (hash of hostname + username)
    - No source code or file contents collected
    - Can be disabled with COSMOS_TELEMETRY=0
    
    Usage:
        tm = Telemetry()
        
        # Track events
        tm.track("compile_success", files=1, duration_ms=8)
        tm.track("compile_e401", files=1, duration_ms=12, error_code="E401")
        tm.track("cache_hit", duration_ms=1)
        tm.track("export_audit", records=100)
        
        # Get metrics
        metrics = tm.get_metrics()
    """
    
    def __init__(self, telemetry_dir: Optional[Path] = None):
        """
        Initialize Telemetry.
        
        Args:
            telemetry_dir: Custom telemetry directory (default: ~/.cosmos/telemetry/)
        """
        # Check if telemetry is enabled
        self.enabled = os.getenv("COSMOS_TELEMETRY", "1") == "1"
        
        if telemetry_dir:
            self.telemetry_dir = telemetry_dir
        else:
            self.telemetry_dir = Path.home() / ".cosmos" / "telemetry"
        
        self.telemetry_dir.mkdir(parents=True, exist_ok=True)
        
        # Get anonymous user ID
        self.user_id = self._get_user_id()
        
        # Event log file
        self.events_file = self.telemetry_dir / "events.jsonl"
    
    def _get_user_id(self) -> str:
        """
        Generate anonymous user ID.
        
        Returns:
            SHA256 hash of hostname + username (first 16 chars)
        """
        id_file = self.telemetry_dir / "user"
        
        # Check for existing ID
        if id_file.exists():
            try:
                return id_file.read_text().strip()
            except:
                pass
        
        # Generate new anonymous ID
        # We use hash of hostname + username, not actual identifiers
        hostname = os.getenv("HOSTNAME", "unknown")
        username = os.getenv("USER", os.getenv("USERNAME", "unknown"))
        
        combined = f"{hostname}-{username}"
        uid = hashlib.sha256(combined.encode()).hexdigest()[:16]
        
        # Save for consistency
        try:
            id_file.write_text(uid)
        except:
            pass
        
        return uid
    
    def track(self, event: str, **props: Any) -> None:
        """
        Track an event.
        
        Args:
            event: Event name (compile_success, compile_e401, cache_hit, export_audit)
            **props: Additional properties (files, duration_ms, error_code, etc.)
        """
        if not self.enabled:
            return
        
        payload = {
            "event": event,
            "user_id": self.user_id,
            "timestamp": int(time.time()),
            "version": "0.4.5-rc1",
            "os": os.name,
            "props": props
        }
        
        # Append to event log
        try:
            with open(self.events_file, "a") as f:
                f.write(json.dumps(payload) + "\n")
        except IOError:
            pass
    
    def get_metrics(self) -> Dict:
        """
        Get aggregated metrics from event log.
        
        Returns:
            Dict with:
            - total_compiles: Total successful compilations
            - total_e401: Total E401 errors
            - cache_hit_rate: Ratio of cache hits
            - unique_users: Count of unique users
            - avg_compile_ms: Average compilation time
        """
        if not self.events_file.exists():
            return {
                "total_compiles": 0,
                "total_e401": 0,
                "cache_hit_rate": 0.0,
                "unique_users": 1,
                "avg_compile_ms": 0.0,
                "total_events": 0
            }
        
        try:
            events = []
            with open(self.events_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except:
                            pass
        except IOError:
            return {
                "total_compiles": 0,
                "total_e401": 0,
                "cache_hit_rate": 0.0,
                "unique_users": 1,
                "avg_compile_ms": 0.0,
                "total_events": 0
            }
        
        # Calculate metrics
        total_events = len(events)
        total_compiles = len([e for e in events if e.get("event") == "compile_success"])
        total_e401 = len([e for e in events if e.get("event") == "compile_e401"])
        cache_hits = len([e for e in events if e.get("event") == "cache_hit"])
        
        # Unique users
        unique_users = len(set(e.get("user_id", "") for e in events))
        
        # Average compile time
        compile_times = [
            e.get("props", {}).get("duration_ms", 0)
            for e in events
            if e.get("event") in ("compile_success", "compile_e401")
        ]
        avg_compile_ms = sum(compile_times) / max(len(compile_times), 1)
        
        # Cache hit rate
        compile_events = total_compiles + total_e401
        cache_hit_rate = cache_hits / max(compile_events + cache_hits, 1)
        
        return {
            "total_compiles": total_compiles,
            "total_e401": total_e401,
            "cache_hit_rate": round(cache_hit_rate, 4),
            "unique_users": unique_users,
            "avg_compile_ms": round(avg_compile_ms, 2),
            "total_events": total_events
        }
    
    def clear(self) -> None:
        """Clear all telemetry data."""
        try:
            if self.events_file.exists():
                self.events_file.unlink()
        except IOError:
            pass
    
    def disable(self) -> None:
        """Disable telemetry."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable telemetry."""
        self.enabled = True


# Singleton instance
_default_telemetry: Optional[Telemetry] = None


def get_telemetry() -> Telemetry:
    """Get singleton Telemetry instance."""
    global _default_telemetry
    if _default_telemetry is None:
        _default_telemetry = Telemetry()
    return _default_telemetry
