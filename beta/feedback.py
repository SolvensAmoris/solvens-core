"""
Feedback Collector - Post-Run Survey System

Captures user feedback after each execution.
Simple file-based for MVP speed.
"""

import json
import time
from dataclasses import dataclass, asdict, field
from typing import Optional, Literal
from pathlib import Path


@dataclass
class Feedback:
    """Feedback entry."""
    id: str
    user_id: Optional[str]
    task: str
    rating: Literal["thumbs_up", "thumbs_down"] = "thumbs_up"
    comment: str = ""
    error_type: Optional[str] = None
    duration_ms: float = 0.0
    steps_completed: int = 0
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return asdict(self)


class FeedbackCollector:
    """
    Collects and analyzes user feedback.
    
    HACK: File-based storage. Use DB for production.
    """
    
    def __init__(self, data_dir: str = "beta_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.feedback_file = self.data_dir / "feedback.json"
        
        if not self.feedback_file.exists():
            self._save([])
    
    def _load(self) -> list:
        if not self.feedback_file.exists():
            return []
        with open(self.feedback_file) as f:
            return json.load(f)
    
    def _save(self, feedback: list):
        with open(self.feedback_file, 'w') as f:
            json.dump(feedback, f, indent=2)
    
    def add(
        self,
        task: str,
        rating: Literal["thumbs_up", "thumbs_down"] = "thumbs_up",
        comment: str = "",
        user_id: Optional[str] = None,
        error_type: Optional[str] = None,
        duration_ms: float = 0.0,
        steps_completed: int = 0,
    ) -> Feedback:
        """Add a feedback entry."""
        import uuid as uuid_module
        
        feedback = Feedback(
            id=str(uuid_module.uuid4())[:8],
            user_id=user_id,
            task=task[:100],  # Truncate
            rating=rating,
            comment=comment[:500],
            error_type=error_type,
            duration_ms=duration_ms,
            steps_completed=steps_completed,
        )
        
        data = self._load()
        data.append(feedback.to_dict())
        self._save(data)
        
        return feedback
    
    def get_all(self) -> list:
        """Get all feedback entries."""
        return [Feedback(**f) for f in self._load()]
    
    def get_stats(self) -> dict:
        """Get feedback statistics."""
        data = self._load()
        
        if not data:
            return {
                "total": 0,
                "positive": 0,
                "negative": 0,
                "positive_rate": 0.0,
                "avg_duration_ms": 0.0,
                "top_issues": [],
            }
        
        positive = sum(1 for f in data if f["rating"] == "thumbs_up")
        negative = sum(1 for f in data if f["rating"] == "thumbs_down")
        
        durations = [f["duration_ms"] for f in data if f["duration_ms"] > 0]
        
        # Count error types
        errors = {}
        for f in data:
            if f.get("error_type"):
                err = f["error_type"]
                errors[err] = errors.get(err, 0) + 1
        
        top_issues = sorted(errors.items(), key=lambda x: -x[1])[:5]
        
        return {
            "total": len(data),
            "positive": positive,
            "negative": negative,
            "positive_rate": positive / len(data) * 100 if data else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "top_issues": top_issues,
        }
    
    def get_recent(self, limit: int = 10) -> list:
        """Get recent feedback."""
        data = self._load()
        return [Feedback(**f) for f in data[-limit:]]
    
    def get_issues(self) -> list:
        """Get all negative feedback (issues)."""
        data = self._load()
        return [Feedback(**f) for f in data if f["rating"] == "thumbs_down"]


# Global instance
_collector: Optional[FeedbackCollector] = None


def get_collector() -> FeedbackCollector:
    global _collector
    if _collector is None:
        _collector = FeedbackCollector()
    return _collector


def add_feedback(**kwargs) -> Feedback:
    """Convenience function."""
    return get_collector().add(**kwargs)
