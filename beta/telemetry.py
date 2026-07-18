"""
Telemetry - Execution Metrics Collection

Logs every run: success, time, error type, user_id.
For beta feedback and improvement tracking.
"""

import json
import time
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Literal
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("cosmos.telemetry")


@dataclass
class RunLog:
    """Log entry for a single run."""
    id: str
    user_id: Optional[str]
    task: str
    plan_id: str
    status: Literal["completed", "failed", "cancelled"] = "completed"
    duration_ms: float = 0.0
    steps_total: int = 0
    steps_completed: int = 0
    cost: float = 0.0
    tokens_used: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    provider: str = "mock"
    created_at: float = field(default_factory=time.time)
    
    @property
    def success(self) -> bool:
        return self.status == "completed"
    
    def to_dict(self) -> dict:
        return asdict(self)


class Telemetry:
    """
    Collects execution telemetry.
    
    Logs every run for:
    - Success rate tracking
    - Performance monitoring
    - Error analysis
    - Usage patterns
    """
    
    def __init__(self, data_dir: str = "beta_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.logs_file = self.data_dir / "telemetry.json"
        
        if not self.logs_file.exists():
            self._save([])
    
    def _load(self) -> list:
        if not self.logs_file.exists():
            return []
        with open(self.logs_file) as f:
            return json.load(f)
    
    def _save(self, logs: list):
        with open(self.logs_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def log_run(
        self,
        plan_id: str,
        task: str,
        status: str = "completed",
        duration_ms: float = 0.0,
        steps_total: int = 0,
        steps_completed: int = 0,
        cost: float = 0.0,
        tokens_used: int = 0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        provider: str = "mock",
    ) -> RunLog:
        """Log a run execution."""
        import uuid
        
        log = RunLog(
            id=str(uuid.uuid4())[:8],
            user_id=user_id,
            task=task[:200],
            plan_id=plan_id,
            status=status,
            duration_ms=duration_ms,
            steps_total=steps_total,
            steps_completed=steps_completed,
            cost=cost,
            tokens_used=tokens_used,
            error_type=error_type,
            error_message=error_message,
            provider=provider,
        )
        
        data = self._load()
        data.append(log.to_dict())
        
        # Keep last 10000 logs
        if len(data) > 10000:
            data = data[-10000:]
        
        self._save(data)
        
        # Also log to console
        logger.info(
            f"Run logged: {plan_id} | {status} | {duration_ms:.0f}ms | "
            f"steps:{steps_completed}/{steps_total}"
        )
        
        return log
    
    def get_stats(self) -> dict:
        """Get telemetry statistics."""
        data = self._load()
        
        if not data:
            return {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "total_cost": 0.0,
                "total_tokens": 0,
            }
        
        completed = sum(1 for r in data if r["status"] == "completed")
        failed = sum(1 for r in data if r["status"] == "failed")
        
        durations = [r["duration_ms"] for r in data if r["duration_ms"] > 0]
        
        return {
            "total_runs": len(data),
            "successful_runs": completed,
            "failed_runs": failed,
            "success_rate": completed / len(data) * 100 if data else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "total_cost": sum(r["cost"] for r in data),
            "total_tokens": sum(r["tokens_used"] for r in data),
        }
    
    def get_errors(self) -> list:
        """Get all failed runs."""
        data = self._load()
        return [r for r in data if r["status"] == "failed"]
    
    def get_recent(self, limit: int = 20) -> list:
        """Get recent runs."""
        data = self._load()
        return data[-limit:]
    
    def get_error_summary(self) -> dict:
        """Get error type summary."""
        data = self._load()
        errors = [r for r in data if r["status"] == "failed"]
        
        if not errors:
            return {"total_errors": 0, "by_type": {}}
        
        by_type = {}
        for e in errors:
            err_type = e.get("error_type") or "unknown"
            by_type[err_type] = by_type.get(err_type, 0) + 1
        
        return {
            "total_errors": len(errors),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])[:10]),
        }


# Global instance
_telemetry: Optional[Telemetry] = None


def get_telemetry() -> Telemetry:
    global _telemetry
    if _telemetry is None:
        _telemetry = Telemetry()
    return _telemetry


def log_run(**kwargs) -> RunLog:
    """Convenience function."""
    return get_telemetry().log_run(**kwargs)
