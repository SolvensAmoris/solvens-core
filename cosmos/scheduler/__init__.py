"""
Cosmos Scheduler Module

DAG-aware parallel execution with:
- HardenedScheduler: production-ready with limits
- TokenBucketRateLimiter: rate limiting
- CircuitBreaker: fault tolerance
"""

from .types import (
    DAGScheduler,
    ScheduleDecision,
)
from .hardened import (
    HardenedScheduler,
    TokenBucketRateLimiter,
    CircuitBreaker,
    CircuitOpenError,
    QueueFullError,
    TaskTimeoutError,
    get_scheduler,
    submit_task,
)

__all__ = [
    # Original
    "DAGScheduler",
    "ScheduleDecision",
    # Hardened
    "HardenedScheduler",
    "TokenBucketRateLimiter",
    "CircuitBreaker",
    "CircuitOpenError",
    "QueueFullError",
    "TaskTimeoutError",
    "get_scheduler",
    "submit_task",
]
