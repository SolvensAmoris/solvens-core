"""
SOLVENS Observability - Prometheus Metrics + Cost Guardrails

Exposes metrics for:
- solvens_run_cost_usd_total{team, workflow}
- solvens_tokens_total{provider, model}
- solvens_cache_hit_ratio
- solvens_run_duration_seconds

Cost guardrails per team with budget alerts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import threading


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    labels: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RunRecord:
    """Record of a workflow execution."""
    run_id: str
    workflow_name: str
    team_id: str
    status: str  # pending, running, done, error
    
    # Costs
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Provider breakdown
    provider_costs: dict = field(default_factory=dict)
    provider_tokens: dict = field(default_factory=dict)


class MetricsCollector:
    """
    Collect and export Prometheus-compatible metrics.
    
    Metrics exposed:
    - solvens_runs_total{team, workflow, status}
    - solvens_run_cost_usd_total{team, workflow, provider}
    - solvens_tokens_total{team, provider, model}
    - solvens_cache_hits_total{team}
    - solvens_cache_misses_total{team}
    - solvens_run_duration_seconds{team, workflow}
    - solvens_active_runs{team}
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._runs: dict[str, RunRecord] = {}
        
        # Provider pricing (2026 rates)
        self._provider_pricing = {
            "openai": {
                "gpt-4o": {"input": 0.0025, "output": 0.01},  # per 1K tokens
                "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            },
            "anthropic": {
                "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-5-haiku": {"input": 0.0008, "output": 0.004},
            },
            "google": {
                "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
                "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
            },
            "ollama": {"local": {"input": 0.0, "output": 0.0}},  # Free
            "deepseek": {
                "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            },
        }
    
    def _make_labels(self, **kwargs) -> str:
        """Create a sorted labels string."""
        parts = [f'{k}="{v}"' for k, v in sorted(kwargs.items())]
        return "{" + ",".join(parts) + "}"
    
    # Counter operations
    def inc_counter(self, name: str, value: float = 1, **labels):
        """Increment a counter metric."""
        key = f"{name}{self._make_labels(**labels)}"
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value
    
    def set_gauge(self, name: str, value: float, **labels):
        """Set a gauge metric."""
        key = f"{name}{self._make_labels(**labels)}"
        with self._lock:
            self._gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, **labels):
        """Observe a value for histogram."""
        key = f"{name}{self._make_labels(**labels)}"
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
    
    # Run tracking
    def start_run(self, run_id: str, workflow_name: str, team_id: str):
        """Record start of a workflow run."""
        run = RunRecord(
            run_id=run_id,
            workflow_name=workflow_name,
            team_id=team_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        with self._lock:
            self._runs[run_id] = run
        
        self.inc_counter("solvens_runs_total", team_id=team_id, workflow=workflow_name, status="started")
        self.set_gauge("solvens_active_runs", self._get_active_runs_count() + 1, team=team_id)
    
    def complete_run(
        self,
        run_id: str,
        status: str,
        input_tokens: int,
        output_tokens: int,
        provider_costs: dict,
        provider_tokens: dict,
        duration_seconds: float,
    ):
        """Record completion of a workflow run."""
        with self._lock:
            if run_id not in self._runs:
                return
            
            run = self._runs[run_id]
            run.status = status
            run.completed_at = datetime.utcnow()
            run.duration_seconds = duration_seconds
            run.input_tokens = input_tokens
            run.output_tokens = output_tokens
            run.cost_usd = sum(provider_costs.values())
            run.provider_costs = provider_costs
            run.provider_tokens = provider_tokens
        
        # Update metrics
        team_id = run.team_id
        workflow = run.workflow_name
        
        self.inc_counter("solvens_runs_total", team_id=team_id, workflow=workflow, status=status)
        self.set_gauge("solvens_active_runs", self._get_active_runs_count(), team=team_id)
        
        for provider, cost in provider_costs.items():
            self.inc_counter("solvens_run_cost_usd_total", cost, team_id=team_id, workflow=workflow, provider=provider)
        
        for provider, tokens in provider_tokens.items():
            self.inc_counter("solvens_tokens_total", tokens, team_id=team_id, provider=provider)
        
        self.observe_histogram("solvens_run_duration_seconds", duration_seconds, team_id=team_id, workflow=workflow)
    
    def record_cache_hit(self, team_id: str):
        """Record a cache hit."""
        self.inc_counter("solvens_cache_hits_total", team_id=team_id)
    
    def record_cache_miss(self, team_id: str):
        """Record a cache miss."""
        self.inc_counter("solvens_cache_misses_total", team_id=team_id)
    
    def _get_active_runs_count(self) -> int:
        """Get count of active runs."""
        return sum(1 for r in self._runs.values() if r.status == "running")
    
    def get_cache_hit_ratio(self, team_id: Optional[str] = None) -> float:
        """Calculate cache hit ratio."""
        with self._lock:
            hits = sum(
                v for k, v in self._counters.items()
                if "solvens_cache_hits" in k and (not team_id or f'team_id="{team_id}"' in k)
            )
            misses = sum(
                v for k, v in self._counters.items()
                if "solvens_cache_misses" in k and (not team_id or f'team_id="{team_id}"' in k)
            )
        
        total = hits + misses
        return hits / total if total > 0 else 0.0
    
    # Prometheus exposition format
    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            # Counters
            for key, value in self._counters.items():
                name = key.split("{")[0]
                labels = key[len(name):]
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{labels} {value}")
            
            # Gauges
            for key, value in self._gauges.items():
                name = key.split("{")[0]
                labels = key[len(name):]
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{labels} {value}")
            
            # Histograms
            for key, values in self._histograms.items():
                name = key.split("{")[0]
                labels = key[len(name):]
                lines.append(f"# TYPE {name} histogram")
                
                # Buckets (1, 5, 10, 30, 60, 120, 300, 600 seconds)
                buckets = [1, 5, 10, 30, 60, 120, 300, 600]
                for bucket in buckets:
                    count = sum(1 for v in values if v <= bucket)
                    lines.append(f'{name}_bucket{labels.replace("}", f",le=\"{bucket}\"}}")} {count}')
                lines.append(f"{name}_sum{labels} {sum(values)}")
                lines.append(f"{name}_count{labels} {len(values)}")
        
        return "\n".join(lines)


class CostGuardrail:
    """
    Enforce cost budgets per team.
    
    Features:
    - Monthly budget limits
    - Alert thresholds
    - Auto-downgrade to cheaper providers
    - Slack/email notifications
    """
    
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self._budgets: dict[str, float] = {}
        self._spent: dict[str, float] = {}
        self._alert_thresholds: dict[str, float] = {}
        self._callbacks: list[callable] = []
    
    def set_budget(self, team_id: str, monthly_budget: float, alert_threshold: float = 0.8):
        """Set monthly budget for a team."""
        self._budgets[team_id] = monthly_budget
        self._spent[team_id] = 0.0
        self._alert_thresholds[team_id] = alert_threshold
    
    def on_alert(self, callback: callable):
        """Register alert callback."""
        self._callbacks.append(callback)
    
    def can_run(self, team_id: str, estimated_cost: float) -> tuple[bool, Optional[str]]:
        """
        Check if team can run a workflow.
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        budget = self._budgets.get(team_id, float("inf"))
        spent = self._spent.get(team_id, 0.0)
        remaining = budget - spent
        
        if spent + estimated_cost > budget:
            return False, f"Budget exceeded: ${spent:.2f}/${budget:.2f}"
        
        # Check alert threshold
        if spent / budget >= self._alert_thresholds.get(team_id, 0.8):
            for callback in self._callbacks:
                callback(team_id, spent, budget, "threshold_exceeded")
        
        return True, None
    
    def record_cost(self, team_id: str, cost: float):
        """Record actual cost spent."""
        self._spent[team_id] = self._spent.get(team_id, 0.0) + cost
        
        # Check if exceeded
        budget = self._budgets.get(team_id)
        if budget and self._spent[team_id] >= budget:
            for callback in self._callbacks:
                callback(team_id, self._spent[team_id], budget, "budget_exceeded")
    
    def get_remaining_budget(self, team_id: str) -> float:
        """Get remaining budget for team."""
        budget = self._budgets.get(team_id, float("inf"))
        spent = self._spent.get(team_id, 0.0)
        return max(0, budget - spent)
    
    def reset_monthly(self, team_id: str):
        """Reset spent amount for new month."""
        self._spent[team_id] = 0.0
    
    def should_use_local(self, team_id: str, estimated_cost: float) -> bool:
        """
        Determine if workflow should use local (free) provider.
        
        Returns True if cost exceeds threshold or budget is tight.
        """
        budget = self._budgets.get(team_id, float("inf"))
        spent = self._spent.get(team_id, 0.0)
        remaining = budget - spent
        
        # Use local if budget is < 10% remaining and cost > $0.50
        if remaining < budget * 0.1 and estimated_cost > 0.50:
            return True
        
        # Use local if estimated cost > $0.50 and already over 80% budget
        if spent > budget * 0.8 and estimated_cost > 0.50:
            return True
        
        return False


# Singleton instance
metrics_collector = MetricsCollector()
cost_guardrail = CostGuardrail(metrics_collector)
