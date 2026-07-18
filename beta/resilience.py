"""
Resilience - Rate Limiting, Circuit Breaker, Queue

Basic scaling and resilience for beta.
"""

import asyncio
import time
import logging
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable, Any
from enum import Enum

logger = logging.getLogger("cosmos.resilience")


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RateLimitConfig:
    max_requests: int = 100
    window_seconds: float = 60.0


class RateLimiter:
    """
    Simple rate limiter using token bucket algorithm.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._tokens = self.config.max_requests
        self._last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        async with self._lock:
            self._refill()
            
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        
        # Add tokens based on rate
        tokens_to_add = elapsed * (self.config.max_requests / self.config.window_seconds)
        self._tokens = min(self.config.max_requests, self._tokens + tokens_to_add)
        self._last_refill = now


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by opening circuit when failures exceed threshold.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if circuit should transition
            self._check_transition()
            
            # If open, reject immediately
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpen(f"Circuit is open. Try again later.")
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info("Circuit breaker CLOSED (recovered)")
    
    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker OPEN after {self._failure_count} failures")
    
    def _check_transition(self):
        """Check if circuit should transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info("Circuit breaker HALF_OPEN (testing recovery)")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class RetryPolicy:
    """
    Retry policy with exponential backoff.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


async def with_retry(
    func: Callable,
    *args,
    policy: Optional[RetryPolicy] = None,
    **kwargs
) -> Any:
    """Execute function with retry policy."""
    policy = policy or RetryPolicy()
    
    last_error = None
    for attempt in range(policy.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < policy.max_retries:
                delay = policy.get_delay(attempt)
                logger.warning(f"Retry {attempt + 1}/{policy.max_retries} after {delay:.1f}s: {e}")
                await asyncio.sleep(delay)
    
    raise last_error


class TaskQueue:
    """
    Simple async task queue with bounded size.
    """
    
    def __init__(self, maxsize: int = 100):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._running = False
    
    async def put(self, item: Any, timeout: Optional[float] = None):
        """Add item to queue."""
        await asyncio.wait_for(self._queue.put(item), timeout=timeout)
    
    async def get(self, timeout: Optional[float] = None) -> Any:
        """Get item from queue."""
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)
    
    def task_done(self):
        """Mark task as done."""
        self._queue.task_done()
    
    async def join(self):
        """Wait for all tasks to complete."""
        await self._queue.join()
    
    @property
    def qsize(self) -> int:
        return self._queue.qsize()
    
    @property
    def empty(self) -> bool:
        return self._queue.empty()
    
    @property
    def full(self) -> bool:
        return self._queue.full()
