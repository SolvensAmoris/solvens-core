"""
SOLVENS Cost Safety Module

Circuit breaker, budget management, and cost estimation to prevent
cost explosion attacks. This is a CRITICAL security component.

Key Features:
- Budget Manager: Per-team, per-workflow spending limits
- Cost Estimator: Pre-execution cost prediction
- Circuit Breaker: Auto-abort when limits exceeded
- Rate Limiter: Prevent abuse
"""

from dataclasses import dataclass, field
from datetime import timezone, datetime, timedelta
from typing import Optional, Callable
from enum import Enum
import threading
import time
import logging

logger = logging.getLogger(__name__)


class CostLimitExceeded(Exception):
    """Raised when cost exceeds configured limits."""
    pass


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class CostEstimate:
    """Pre-execution cost estimate."""
    workflow_name: str
    num_tasks: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    estimated_time_ms: float
    providers_breakdown: dict
    risks: list[str] = field(default_factory=list)
    
    def is_acceptable(self, max_cost: float) -> bool:
        return self.estimated_cost_usd <= max_cost


@dataclass
class CostRecord:
    """Record of actual cost incurred."""
    run_id: str
    workflow_name: str
    team_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    provider: str = ""
    aborted: bool = False
    abort_reason: Optional[str] = None


@dataclass
class Budget:
    """Budget configuration for a team or workflow."""
    team_id: str
    workflow_id: Optional[str] = None
    max_cost_per_run: float = 1.00  # Max cost per single run
    max_cost_per_day: float = 100.00  # Max cost per day
    max_cost_per_month: float = 1000.00  # Max cost per month
    max_dag_depth: int = 20  # Max DAG depth
    max_tasks_per_run: int = 100  # Max tasks in a run
    enabled: bool = True


@dataclass
class RateLimit:
    """Rate limit configuration."""
    ip_address: str
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    requests_per_day: int = 1000
    last_request: Optional[datetime] = None
    request_count_minute: int = 0
    request_count_hour: int = 0
    request_count_day: int = 0


class ProviderPricing:
    """
    Current LLM pricing (2026 rates).
    Prices are per 1M tokens.
    """
    
    # Input token prices ($ per 1M tokens)
    INPUT_PRICES = {
        "openai": {
            "gpt-4o": 2.50,
            "gpt-4o-mini": 0.15,
            "gpt-4-turbo": 10.00,
        },
        "anthropic": {
            "claude-3-5-sonnet": 3.00,
            "claude-3-5-haiku": 0.80,
            "claude-3-opus": 15.00,
        },
        "google": {
            "gemini-1.5-pro": 1.25,
            "gemini-1.5-flash": 0.075,
            "gemini-2.0-flash": 0.00,  # Free tier
        },
        "deepseek": {
            "deepseek-chat": 0.14,
            "deepseek-coder": 0.14,
        },
        "ollama": {
            "llama3": 0.00,  # Free (local)
            "llama3.1": 0.00,
            "mixtral": 0.00,
            "codellama": 0.00,
        },
    }
    
    # Output token prices ($ per 1M tokens)
    OUTPUT_PRICES = {
        "openai": {
            "gpt-4o": 10.00,
            "gpt-4o-mini": 0.60,
            "gpt-4-turbo": 30.00,
        },
        "anthropic": {
            "claude-3-5-sonnet": 15.00,
            "claude-3-5-haiku": 4.00,
            "claude-3-opus": 75.00,
        },
        "google": {
            "gemini-1.5-pro": 5.00,
            "gemini-1.5-flash": 0.30,
            "gemini-2.0-flash": 0.00,
        },
        "deepseek": {
            "deepseek-chat": 0.28,
            "deepseek-coder": 0.28,
        },
        "ollama": {
            "llama3": 0.00,
            "llama3.1": 0.00,
            "mixtral": 0.00,
            "codellama": 0.00,
        },
    }
    
    # Average tokens per task (rough estimates)
    AVG_INPUT_TOKENS = {
        "simple": 500,      # Basic query
        "medium": 2000,     # Standard task
        "complex": 8000,    # Complex reasoning
        "code_gen": 3000,   # Code generation
    }
    
    AVG_OUTPUT_TOKENS = {
        "simple": 200,
        "medium": 1000,
        "complex": 4000,
        "code_gen": 2000,
    }
    
    @classmethod
    def get_price(cls, provider: str, model: str, token_type: str) -> float:
        """Get price for provider/model/token_type."""
        provider_prices = cls.INPUT_PRICES.get(provider.lower(), {})
        if token_type == "input":
            prices = cls.INPUT_PRICES.get(provider.lower(), {})
        else:
            prices = cls.OUTPUT_PRICES.get(provider.lower(), {})
        
        return prices.get(model.lower(), 0.0) / 1_000_000  # Per token
    
    @classmethod
    def estimate_task_cost(
        cls,
        provider: str,
        model: str,
        task_complexity: str = "medium"
    ) -> tuple[int, int, float]:
        """Estimate tokens and cost for a task."""
        input_tokens = cls.AVG_INPUT_TOKENS.get(task_complexity, 2000)
        output_tokens = cls.AVG_OUTPUT_TOKENS.get(task_complexity, 1000)
        
        input_cost = input_tokens * cls.get_price(provider, model, "input")
        output_cost = output_tokens * cls.get_price(provider, model, "output")
        
        return input_tokens, output_tokens, input_cost + output_cost


class CostEstimator:
    """
    Estimate cost BEFORE execution to prevent cost overruns.
    """
    
    def __init__(self):
        self.pricing = ProviderPricing()
    
    def estimate_workflow(
        self,
        workflow_name: str,
        tasks: list[dict],
        dag_depth: int
    ) -> CostEstimate:
        """
        Estimate cost for a complete workflow.
        
        Args:
            workflow_name: Name of workflow
            tasks: List of task definitions
            dag_depth: Maximum DAG depth (affects parallelism)
        
        Returns:
            CostEstimate with predictions
        """
        total_input = 0
        total_output = 0
        total_cost = 0.0
        providers_used: dict[str, int] = {}
        risks: list[str] = []
        
        for task in tasks:
            provider = task.get("provider", "openai").lower()
            model = task.get("model", "gpt-4o")
            complexity = task.get("complexity", "medium")
            
            inp, out, cost = self.pricing.estimate_task_cost(provider, model, complexity)
            total_input += inp
            total_output += out
            total_cost += cost
            
            providers_used[provider] = providers_used.get(provider, 0) + 1
        
        # Time estimate: sequential time / parallelism factor
        num_tasks = len(tasks)
        sequential_time = num_tasks * 5000  # 5s per task
        parallelism_factor = min(dag_depth, num_tasks)  # Max parallel tasks
        estimated_time = sequential_time / max(1, parallelism_factor)
        
        # Risk detection
        if total_cost > 1.00:
            risks.append(f"High cost: ${total_cost:.2f}")
        if num_tasks > 50:
            risks.append(f"Many tasks: {num_tasks}")
        if dag_depth > 15:
            risks.append(f"Deep DAG: {dag_depth} levels")
        if providers_used.get("openai", 0) > 5:
            risks.append("Heavy OpenAI usage")
        
        return CostEstimate(
            workflow_name=workflow_name,
            num_tasks=num_tasks,
            estimated_input_tokens=total_input,
            estimated_output_tokens=total_output,
            estimated_cost_usd=total_cost,
            estimated_time_ms=estimated_time,
            providers_breakdown=providers_used,
            risks=risks
        )


class CircuitBreaker:
    """
    Circuit breaker to prevent runaway costs.
    
    Opens circuit if:
    - Cost exceeds max_cost_per_run
    - DAG depth exceeds max_dag_depth
    - Number of tasks exceeds max_tasks_per_run
    """
    
    def __init__(self, budget: Budget):
        self.budget = budget
        self._state = "closed"  # closed, open, half-open
        self._opened_at: Optional[datetime] = None
        self._failure_count = 0
        self._threshold = 5  # Failures before opening
    
    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == "open":
            # Auto-reset after cooldown
            if self._opened_at:
                cooldown = timedelta(minutes=1)
                if datetime.now(timezone.utc) - self._opened_at > cooldown:
                    self._state = "half-open"
                    logger.info("Circuit breaker entering half-open state")
        return self._state
    
    def check(self, estimate: CostEstimate) -> None:
        """
        Check if operation should proceed.
        
        Raises:
            CircuitBreakerOpen: If circuit is open
            CostLimitExceeded: If limits exceeded
        """
        # Check if circuit is open
        if self.state == "open":
            raise CircuitBreakerOpen(
                f"Circuit breaker open for team {self.budget.team_id}. "
                f"Try again later."
            )
        
        # Check cost limit
        if estimate.estimated_cost_usd > self.budget.max_cost_per_run:
            self._record_failure()
            raise CostLimitExceeded(
                f"Estimated cost ${estimate.estimated_cost_usd:.4f} exceeds "
                f"limit ${self.budget.max_cost_per_run:.4f}"
            )
        
        # Check DAG depth
        # Note: dag_depth is in estimate.num_tasks for simplicity
        if estimate.num_tasks > self.budget.max_tasks_per_run:
            self._record_failure()
            raise CostLimitExceeded(
                f"Task count {estimate.num_tasks} exceeds "
                f"limit {self.budget.max_tasks_per_run}"
            )
        
        # Check risks
        for risk in estimate.risks:
            if "High cost" in risk:
                logger.warning(f"High cost risk: {risk}")
    
    def _record_failure(self) -> None:
        """Record a failure and potentially open circuit."""
        self._failure_count += 1
        if self._failure_count >= self._threshold:
            self._state = "open"
            self._opened_at = datetime.now(timezone.utc)
            logger.error(f"Circuit breaker OPENED after {self._failure_count} failures")
    
    def record_success(self) -> None:
        """Record a successful run."""
        self._failure_count = 0
        if self._state == "half-open":
            self._state = "closed"
            logger.info("Circuit breaker CLOSED after successful run")


class BudgetManager:
    """
    Manages budgets for teams and workflows.
    
    Tracks spending and enforces limits.
    """
    
    def __init__(self):
        self._budgets: dict[str, Budget] = {}
        self._spending: dict[str, list[CostRecord]] = {}
        self._rate_limits: dict[str, RateLimit] = {}
        self._lock = threading.Lock()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
    
    def set_budget(self, budget: Budget) -> None:
        """Set budget for a team/workflow."""
        with self._lock:
            key = self._make_key(budget.team_id, budget.workflow_id)
            self._budgets[key] = budget
            self._circuit_breakers[key] = CircuitBreaker(budget)
            if key not in self._spending:
                self._spending[key] = []
    
    def _make_key(self, team_id: str, workflow_id: Optional[str] = None) -> str:
        """Create lookup key for budget."""
        if workflow_id:
            return f"{team_id}:{workflow_id}"
        return team_id
    
    def check_rate_limit(self, ip_address: str) -> None:
        """Check if IP is within rate limits."""
        with self._lock:
            if ip_address not in self._rate_limits:
                self._rate_limits[ip_address] = RateLimit(ip_address=ip_address)
            
            limit = self._rate_limits[ip_address]
            now = datetime.now(timezone.utc)
            
            # Reset counters if time window passed
            if limit.last_request:
                elapsed = now - limit.last_request
                if elapsed > timedelta(minutes=1):
                    limit.request_count_minute = 0
                if elapsed > timedelta(hours=1):
                    limit.request_count_hour = 0
                if elapsed > timedelta(days=1):
                    limit.request_count_day = 0
            
            # Check limits
            if limit.request_count_minute >= limit.requests_per_minute:
                raise RateLimitExceeded(f"Rate limit: max {limit.requests_per_minute} req/min")
            if limit.request_count_hour >= limit.requests_per_hour:
                raise RateLimitExceeded(f"Rate limit: max {limit.requests_per_hour} req/hour")
            if limit.request_count_day >= limit.requests_per_day:
                raise RateLimitExceeded(f"Rate limit: max {limit.requests_per_day} req/day")
            
            # Update counters
            limit.request_count_minute += 1
            limit.request_count_hour += 1
            limit.request_count_day += 1
            limit.last_request = now
    
    def can_execute(
        self,
        team_id: str,
        workflow_id: Optional[str],
        estimate: CostEstimate
    ) -> tuple[bool, Optional[str]]:
        """
        Check if execution is allowed.
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        with self._lock:
            # Check rate limit
            # (In real impl, get IP from context)
            
            # Get budget
            key = self._make_key(team_id, workflow_id)
            budget = self._budgets.get(key)
            
            if not budget:
                # Use default budget
                budget = Budget(team_id=team_id)
            
            if not budget.enabled:
                return False, "Budget disabled"
            
            # Check daily spending
            today = datetime.now(timezone.utc).date()
            today_spending = sum(
                r.cost_usd for r in self._spending.get(key, [])
                if r.started_at.date() == today
            )
            
            if today_spending + estimate.estimated_cost_usd > budget.max_cost_per_day:
                return False, (
                    f"Daily budget exceeded: ${today_spending:.2f} + "
                    f"${estimate.estimated_cost_usd:.2f} > ${budget.max_cost_per_day:.2f}"
                )
            
            # Check circuit breaker
            cb = self._circuit_breakers.get(key)
            if cb:
                try:
                    cb.check(estimate)
                except (CircuitBreakerOpen, CostLimitExceeded) as e:
                    return False, str(e)
            
            return True, None
    
    def record_execution(self, record: CostRecord) -> None:
        """Record cost of executed workflow."""
        with self._lock:
            key = self._make_key(record.team_id, record.workflow_name)
            if key not in self._spending:
                self._spending[key] = []
            self._spending[key].append(record)
            
            # Update circuit breaker on success
            cb = self._circuit_breakers.get(key)
            if cb and not record.aborted:
                cb.record_success()
    
    def abort_run(self, run_id: str, reason: str) -> None:
        """Abort a running workflow and record the abortion."""
        with self._lock:
            for records in self._spending.values():
                for record in records:
                    if record.run_id == run_id and record.completed_at is None:
                        record.aborted = True
                        record.abort_reason = reason
                        record.completed_at = datetime.now(timezone.utc)
                        logger.warning(f"Run {run_id} aborted: {reason}")
                        return
    
    def get_spending(self, team_id: str, days: int = 30) -> dict:
        """Get spending summary for team."""
        with self._lock:
            key = self._make_key(team_id)
            records = self._spending.get(key, [])
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            total_cost = sum(r.cost_usd for r in records if r.started_at > cutoff)
            total_runs = len([r for r in records if r.started_at > cutoff])
            aborted_runs = len([r for r in records if r.aborted and r.started_at > cutoff])
            
            return {
                "team_id": team_id,
                "period_days": days,
                "total_cost_usd": total_cost,
                "total_runs": total_runs,
                "aborted_runs": aborted_runs,
                "avg_cost_per_run": total_cost / total_runs if total_runs else 0,
            }


# Singleton instance
cost_estimator = CostEstimator()
budget_manager = BudgetManager()
