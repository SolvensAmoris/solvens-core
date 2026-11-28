"""Agent Orchestrator - Central coordination for all agent operations."""

from __future__ import annotations

import asyncio
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timezone, datetime
from typing import Any, Awaitable, Callable, TypeVar, TYPE_CHECKING

import structlog

from solvens.core.base import BaseService
from solvens.core.exceptions import (
    OrchestratorError,
    TaskError,
    TaskNotFoundError,
    TaskTimeoutError,
)
from solvens.core.types import (
    Message,
    Response,
    Task,
    TaskPriority,
    TaskStatus,
)
from solvens.router.router import CapabilityRouter

if TYPE_CHECKING:
    from solvens.persistence.worker import DurableTaskWorker

DurableHandler = Callable[[dict[str, Any]], Awaitable[Any]]

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator.
    
    Attributes:
        max_concurrent_tasks: Maximum concurrent tasks
        task_timeout: Default task timeout in seconds
        max_retries: Maximum retry attempts
        enable_parallel: Enable parallel task execution
        queue_size: Maximum queue size
    """
    
    max_concurrent_tasks: int = 10
    task_timeout: int = 300
    max_retries: int = 3
    enable_parallel: bool = True
    queue_size: int = 1000
    durable_workers: int = 0
    durable_lease_seconds: int = 60
    durable_poll_interval: float = 1.0


class TaskResult:
    """Result of a task execution.
    
    Attributes:
        task_id: Task identifier
        status: Final task status
        result: Task result data
        error: Error message if failed
        duration: Execution duration in seconds
    """
    
    def __init__(
        self,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: str | None = None,
        duration: float = 0.0,
    ):
        self.task_id = task_id
        self.status = status
        self.result = result
        self.error = error
        self.duration = duration


class AgentOrchestrator(BaseService[None]):
    """Central orchestrator for agent operations.
    
    Manages task execution, coordination, queuing, and resource allocation
    for all agents in the system.
    
    Features:
    - Task queuing with priorities
    - Parallel and sequential execution
    - Automatic retries with exponential backoff
    - Task cancellation
    - Resource management
    - Event hooks
    """
    
    def __init__(self, config: OrchestratorConfig | None = None):
        super().__init__()
        self.config = config or OrchestratorConfig()
        self._tasks: dict[str, Task] = {}
        self._task_queue: asyncio.PriorityQueue[tuple[int, Task]] | None = None
        self._workers: list[asyncio.Task[None]] = []
        self._router: CapabilityRouter | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._running_tasks: set[str] = set()
        self._cancelled_tasks: set[str] = set()
        self._event_hooks: dict[str, list[Callable]] = {
            "task_start": [],
            "task_complete": [],
            "task_fail": [],
            "task_cancel": [],
        }
        self._lock = asyncio.Lock()
        self._durable_handlers: dict[str, DurableHandler] = {}
        self._durable_workers: list[DurableTaskWorker] = []
        self._durable_worker_tasks: list[asyncio.Task[None]] = []

    @property
    def durable_enabled(self) -> bool:
        """Whether database-backed workers are configured and running."""
        return bool(self._durable_workers)

    def register_durable_handler(self, name: str, handler: DurableHandler) -> None:
        """Register a named, serializable task handler before initialization."""
        if not name or len(name) > 128:
            raise ValueError("durable handler name must contain 1..128 characters")
        if name in self._durable_handlers:
            raise ValueError(f"durable handler already registered: {name}")
        self._durable_handlers[name] = handler

    async def submit_durable_task(
        self,
        *,
        tenant_id: str,
        user_id: str,
        handler_name: str,
        payload: dict[str, Any],
        priority: int = 0,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
    ) -> str:
        """Persist a durable task for execution by any configured worker."""
        if not self._durable_workers:
            raise OrchestratorError("Durable workers are not configured")
        return await self._durable_workers[0].submit_task(
            tenant_id=tenant_id,
            user_id=user_id,
            handler_name=handler_name,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key,
        )

    async def initialize(self) -> None:
        """Initialize the orchestrator."""
        logger.info("Initializing AgentOrchestrator", config=self.config)
        
        self._task_queue = asyncio.PriorityQueue(maxsize=self.config.queue_size)
        self._router = CapabilityRouter()
        await self._router.initialize()
        
        if self.config.enable_parallel:
            self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_tasks)
        
        # Start process-local callback workers.
        for i in range(self.config.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        # Import storage dependencies only when durable workers are enabled.
        if self.config.durable_workers > 0:
            from solvens.persistence.worker import DurableTaskWorker

        # Durable workers claim database records with SKIP LOCKED and leases.
        for i in range(max(0, self.config.durable_workers)):
            worker_id = f"{socket.gethostname()[:48]}:{uuid.uuid4().hex}"
            durable_worker = DurableTaskWorker(
                worker_id=worker_id,
                handlers=self._durable_handlers,
                lease_seconds=self.config.durable_lease_seconds,
                poll_interval=self.config.durable_poll_interval,
            )
            self._durable_workers.append(durable_worker)
            self._durable_worker_tasks.append(
                asyncio.create_task(durable_worker.run(), name=f"durable-worker-{i}")
            )

        logger.info(
            "AgentOrchestrator initialized",
            workers=len(self._workers),
            durable_workers=len(self._durable_workers),
        )

    async def shutdown(self) -> None:
        """Shutdown the orchestrator gracefully."""
        logger.info("Shutting down AgentOrchestrator")
        
        # Stop durable workers. In-flight work is recovered after lease expiry.
        for worker in self._durable_workers:
            worker.stop()
        for worker_task in self._durable_worker_tasks:
            worker_task.cancel()
        await asyncio.gather(*self._durable_worker_tasks, return_exceptions=True)
        self._durable_worker_tasks.clear()
        self._durable_workers.clear()

        # Cancel process-local workers
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        
        # Shutdown router
        if self._router:
            await self._router.shutdown()
        
        logger.info("AgentOrchestrator shutdown complete")

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tasks from the queue."""
        logger.debug("Worker started", worker_id=worker_id)
        
        while True:
            try:
                priority, task = await self._task_queue.get()
                
                if task.id in self._cancelled_tasks:
                    task.cancel()
                    await self._emit_event("task_cancel", task)
                    self._task_queue.task_done()
                    continue
                
                await self._execute_task(task)
                self._task_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker error", worker_id=worker_id, error=str(e))

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        start_time = datetime.now(timezone.utc)
        
        try:
            task.start()
            self._running_tasks.add(task.id)
            await self._emit_event("task_start", task)
            
            logger.info("Executing task", task_id=task.id, description=task.description)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                task.metadata.get("callback")(),
                timeout=task.metadata.get("timeout", self.config.task_timeout),
            )
            
            task.complete(result)
            logger.info("Task completed", task_id=task.id)
            
        except asyncio.TimeoutError:
            task.fail(f"Task timed out after {self.config.task_timeout}s")
            logger.error("Task timed out", task_id=task.id)
            
        except Exception as e:
            task.fail(str(e))
            logger.error("Task failed", task_id=task.id, error=str(e))
            
        finally:
            self._running_tasks.discard(task.id)
            
            if task.status == TaskStatus.COMPLETED:
                await self._emit_event("task_complete", task)
            else:
                await self._emit_event("task_fail", task)

    # === Public API ===

    def create_task(
        self,
        description: str,
        callback: Callable[[], Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        **metadata: Any,
    ) -> Task:
        """Create a new task.
        
        Args:
            description: Human-readable task description
            callback: Async callable to execute
            priority: Task priority level
            **metadata: Additional task metadata
            
        Returns:
            Created Task instance
        """
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            priority=priority,
            metadata={"callback": callback, **metadata},
        )
        self._tasks[task.id] = task
        return task

    async def submit_task(
        self,
        description: str,
        callback: Callable[[], Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        **metadata: Any,
    ) -> str:
        """Submit a task to the queue.
        
        Args:
            description: Task description
            callback: Async callable to execute
            priority: Task priority
            **metadata: Additional metadata
            
        Returns:
            Task ID
        """
        task = self.create_task(description, callback, priority, **metadata)
        
        # Priority is inverted for queue (lower number = higher priority)
        priority_value = self._priority_value(priority)
        await self._task_queue.put((priority_value, task))
        
        logger.info("Task submitted", task_id=task.id, priority=priority.value)
        return task.id

    async def execute_task(
        self,
        description: str,
        callback: Callable[[], Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int | None = None,
    ) -> TaskResult:
        """Execute a task directly (not queued).
        
        Args:
            description: Task description
            callback: Async callable
            priority: Task priority
            timeout: Optional timeout override
            
        Returns:
            TaskResult with execution outcome
        """
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            priority=priority,
            metadata={"callback": callback, "timeout": timeout or self.config.task_timeout},
        )
        self._tasks[task.id] = task
        
        start_time = datetime.now(timezone.utc)
        await self._execute_task(task)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return TaskResult(
            task_id=task.id,
            status=task.status,
            result=task.result,
            error=task.error,
            duration=duration,
        )

    async def cancel_durable_task(
        self, *, task_id: str, tenant_id: str, user_id: str
    ) -> bool:
        """Cancel a persisted task only when tenant and owner match."""
        if not self._durable_workers:
            raise OrchestratorError("Durable workers are not configured")
        return await self._durable_workers[0].cancel_task(
            task_id=task_id, tenant_id=tenant_id, user_id=user_id
        )

    async def route_message(
        self,
        messages: list[Message],
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Route a message to an appropriate provider.
        
        Args:
            messages: Conversation messages
            model: Optional model preference
            provider: Optional provider preference
            
        Returns:
            Provider response content
        """
        if not self._router:
            raise OrchestratorError("Router not initialized")
        
        return await self._router.route(
            messages=messages,
            preferred_model=model,
            preferred_provider=provider,
        )

    def get_task(self, task_id: str) -> Task:
        """Get a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task instance
            
        Raises:
            TaskNotFoundError: If task not found
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return self._tasks[task_id]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if cancelled, False if already completed
        """
        task = self.get_task(task_id)
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False
        
        self._cancelled_tasks.add(task_id)
        task.cancel()
        await self._emit_event("task_cancel", task)
        
        logger.info("Task cancelled", task_id=task_id)
        return True

    async def retry_task(self, task_id: str) -> str:
        """Retry a failed task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            New task ID
        """
        task = self.get_task(task_id)
        
        if task.status != TaskStatus.FAILED:
            raise TaskError(f"Cannot retry task with status {task.status}")
        
        callback = task.metadata.get("callback")
        if not callback:
            raise TaskError("No callback found for task")
        
        # Create new task with same parameters
        return await self.submit_task(
            description=f"Retry: {task.description}",
            callback=callback,
            priority=task.priority,
        )

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[Task]:
        """List tasks with optional filtering.
        
        Args:
            status: Filter by status
            limit: Maximum number of tasks
            
        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]

    # === Event System ===

    def on(self, event: str, callback: Callable) -> None:
        """Register an event handler.
        
        Args:
            event: Event name
            callback: Handler function
        """
        if event in self._event_hooks:
            self._event_hooks[event].append(callback)

    async def _emit_event(self, event: str, task: Task) -> None:
        """Emit an event to all registered handlers."""
        handlers = self._event_hooks.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(task)
                else:
                    handler(task)
            except Exception as e:
                logger.error("Event handler error", event=event, error=str(e))

    # === Utilities ===

    @staticmethod
    def _priority_value(priority: TaskPriority) -> int:
        """Convert priority to numeric value for queue."""
        values = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }
        return values.get(priority, 2)

    @property
    def stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_tasks": len(self._tasks),
            "running_tasks": len(self._running_tasks),
            "queued_tasks": self._task_queue.qsize() if self._task_queue else 0,
            "workers": len(self._workers),
            "durable_workers": len(self._durable_workers),
            "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
        }
