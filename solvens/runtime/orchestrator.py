"""
solvens/runtime/orchestrator.py
===============================

ULTRA-LIGHT ORCHESTRATOR v0.2
Orchestrator + Scheduler + Planner fusionados.

Un solo archivo que maneja tasks con asyncio + priority queue.
No overkill hasta que duela.

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
from collections import defaultdict
import heapq

logger = logging.getLogger("solvens.runtime")


# ============================================================
# ENUMS Y TIPOS
# ============================================================

class TaskPriority(Enum):
    """Prioridad de tasks (menor número = mayor prioridad)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    """Estado de task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult:
    """Resultado de una task."""
    
    def __init__(
        self,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: Optional[str] = None,
        duration_ms: float = 0,
        cost: float = 0,
        provider: str = "unknown"
    ):
        self.task_id = task_id
        self.status = status
        self.result = result
        self.error = error
        self.duration_ms = duration_ms
        self.cost = cost
        self.provider = provider


# ============================================================
# TASK
# ============================================================

@dataclass
class Task:
    """
    Task ejecutable por el runtime.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        func: Async function to execute
        args: Positional arguments
        kwargs: Keyword arguments
        priority: Task priority
        timeout: Timeout in seconds
        retry: Max retries on failure
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 60.0
    retry: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    
    def __lt__(self, other: Task) -> bool:
        """Para priority queue."""
        return self.priority.value < other.priority.value
    
    @property
    def duration_ms(self) -> float:
        """Duración en milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return 0
    
    @property
    def pending_duration(self) -> float:
        """Tiempo esperando en cola."""
        start = self.started_at or time.time()
        return (start - self.created_at) * 1000


# ============================================================
# PLUGINS (simples para v1)
# ============================================================

@dataclass
class Plugin:
    """Plugin simple para el runtime."""
    name: str
    version: str = "0.1.0"
    enabled: bool = True
    
    async def on_task_start(self, task: Task) -> None:
        """Hook antes de ejecutar task."""
        pass
    
    async def on_task_end(self, task: Task, result: TaskResult) -> None:
        """Hook después de ejecutar task."""
        pass
    
    async def on_error(self, task: Task, error: Exception) -> None:
        """Hook cuando hay error."""
        pass


# ============================================================
# RUNTIME ORCHESTRATOR
# ============================================================

class RuntimeOrchestrator:
    """
    Runtime ultra-light que fusiona:
    - Orchestrator: Ejecuta tasks
    - Scheduler: Priority queue + async execution
    - Planner: Divide tasks complejas
    
    Features:
    - Priority queue con heap
    - Concurrent execution con semaphore
    - Auto-retry con backoff
    - Plugin hooks
    - Metrics y stats
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        enable_metrics: bool = True
    ):
        self.max_concurrent = max_concurrent
        self.enable_metrics = enable_metrics
        
        # Task queue (priority heap)
        self._queue: List[Task] = []
        self._queue_lock = asyncio.Lock()
        
        # Active tasks
        self._active: Dict[str, Task] = {}
        self._active_lock = asyncio.Lock()
        
        # Completed tasks (circular buffer)
        self._completed: List[TaskResult] = []
        self._completed_max = 1000
        
        # Plugins
        self._plugins: List[Plugin] = []
        
        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Stats
        self._stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "avg_latency_ms": 0,
        }
        
        # Control
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
        logger.info(f"RuntimeOrchestrator initialized (max_concurrent={max_concurrent})")
    
    # --------------------------------------------------------
    # PLUGIN MANAGEMENT
    # --------------------------------------------------------
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Registra un plugin."""
        self._plugins.append(plugin)
        logger.info(f"Plugin registered: {plugin.name}")
    
    async def _call_plugins(self, method: str, *args, **kwargs) -> None:
        """Llama un método en todos los plugins."""
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                hook = getattr(plugin, method, None)
                if hook:
                    await hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Plugin {plugin.name}.{method} failed: {e}")
    
    # --------------------------------------------------------
    # SUBMIT TASKS
    # --------------------------------------------------------
    
    async def submit(
        self,
        func: Callable,
        *args,
        name: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 60.0,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Submit una task a la cola.
        
        Returns:
            Task ID
        """
        task = Task(
            id=str(uuid.uuid4())[:8],
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
        )
        
        async with self._queue_lock:
            heapq.heappush(self._queue, task)
        
        self._stats["tasks_submitted"] += 1
        logger.debug(f"Task submitted: {task.id} ({task.name})")
        
        return task.id
    
    async def submit_batch(self, tasks: List[Dict]) -> List[str]:
        """Submit múltiples tasks."""
        task_ids = []
        for t in tasks:
            task_id = await self.submit(
                func=t["func"],
                *t.get("args", []),
                name=t.get("name", ""),
                priority=TaskPriority[t.get("priority", "NORMAL")],
                **t.get("kwargs", {})
            )
            task_ids.append(task_id)
        return task_ids
    
    # --------------------------------------------------------
    # WORKER LOOP
    # --------------------------------------------------------
    
    async def start(self) -> None:
        """Inicia el worker loop."""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Runtime started")
    
    async def stop(self) -> None:
        """Detiene el worker loop."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Runtime stopped")
    
    async def _worker_loop(self) -> None:
        """Worker loop principal."""
        while self._running:
            try:
                # Get next task from queue
                async with self._queue_lock:
                    if not self._queue:
                        await asyncio.sleep(0.1)
                        continue
                    
                    task = heapq.heappop(self._queue)
                
                # Execute task
                asyncio.create_task(self._execute_task(task))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: Task) -> TaskResult:
        """Ejecuta una task individual."""
        async with self._semaphore:  # Concurrency limit
            async with self._active_lock:
                self._active[task.id] = task
            
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            await self._call_plugins("on_task_start", task)
            
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(task.func):
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    # Sync function in thread pool
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs)),
                        timeout=task.timeout
                    )
                
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = time.time()
                
                task_result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    duration_ms=task.duration_ms,
                    provider=task.metadata.get("provider", "unknown")
                )
                
                self._stats["tasks_completed"] += 1
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.FAILED
                task.error = f"Timeout after {task.timeout}s"
                task_result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=task.error,
                    duration_ms=task.duration_ms
                )
                self._stats["tasks_failed"] += 1
                logger.warning(f"Task {task.id} timed out")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task_result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    duration_ms=task.duration_ms
                )
                self._stats["tasks_failed"] += 1
                
                await self._call_plugins("on_error", task, e)
                
                # Retry logic
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    task.started_at = None
                    async with self._queue_lock:
                        heapq.heappush(self._queue, task)
                    logger.info(f"Task {task.id} retry {task.retry_count}/{task.max_retries}")
            finally:
                async with self._active_lock:
                    self._active.pop(task.id, None)
                
                await self._call_plugins("on_task_end", task, task_result)
                
                # Store result
                self._completed.append(task_result)
                if len(self._completed) > self._completed_max:
                    self._completed.pop(0)
        
        return task_result
    
    # --------------------------------------------------------
    # TASK MANAGEMENT
    # --------------------------------------------------------
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Obtiene una task por ID."""
        async with self._active_lock:
            if task_id in self._active:
                return self._active[task_id]
        
        # Check queue
        async with self._queue_lock:
            for task in self._queue:
                if task.id == task_id:
                    return task
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancela una task."""
        task = await self.get_task(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            return True
        return False
    
    async def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[TaskResult]:
        """Espera y retorna resultado de task."""
        start = time.time()
        while time.time() - start < timeout:
            task = await self.get_task(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return TaskResult(
                    task_id=task.id,
                    status=task.status,
                    result=task.result,
                    error=task.error,
                    duration_ms=task.duration_ms
                )
            await asyncio.sleep(0.1)
        return None
    
    # --------------------------------------------------------
    # STATS & METRICS
    # --------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del runtime."""
        return {
            **self._stats,
            "queue_size": len(self._queue),
            "active_tasks": len(self._active),
            "plugins_count": len(self._plugins),
        }
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def queue_size(self) -> int:
        return len(self._queue)
    
    @property
    def active_count(self) -> int:
        return len(self._active)


# ============================================================
# GLOBAL RUNTIME (singleton para CLI)
# ============================================================

_runtime: Optional[RuntimeOrchestrator] = None


def get_runtime() -> RuntimeOrchestrator:
    """Obtiene o crea el runtime global."""
    global _runtime
    if _runtime is None:
        _runtime = RuntimeOrchestrator()
    return _runtime


async def init_runtime(**kwargs) -> RuntimeOrchestrator:
    """Inicializa el runtime global."""
    global _runtime
    _runtime = RuntimeOrchestrator(**kwargs)
    await _runtime.start()
    return _runtime


async def shutdown_runtime() -> None:
    """Detiene el runtime global."""
    global _runtime
    if _runtime:
        await _runtime.stop()
        _runtime = None


# ============================================================
# DECORATORS
# ============================================================

def task(
    name: str = "",
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout: float = 60.0,
    max_retries: int = 3
):
    """Decorator para marcar funciones como tasks."""
    def decorator(func: Callable) -> Callable:
        func._is_task = True
        func._task_name = name
        func._task_priority = priority
        func._task_timeout = timeout
        func._task_max_retries = max_retries
        return func
    return decorator


# ============================================================
# DEMO
# ============================================================

async def demo():
    """Demo del runtime."""
    print("=" * 60)
    print("RUNTIME ORCHESTRATOR v0.2 DEMO")
    print("=" * 60)
    
    runtime = RuntimeOrchestrator(max_concurrent=5)
    await runtime.start()
    
    # Demo tasks
    async def quick_task(name: str, delay: float = 0.5):
        await asyncio.sleep(delay)
        return f"Done: {name}"
    
    async def failing_task():
        await asyncio.sleep(0.1)
        raise ValueError("Simulated failure")
    
    # Submit tasks
    print("\n[Submitting tasks...]")
    
    for i in range(5):
        await runtime.submit(
            quick_task,
            f"Task-{i}",
            name=f"QuickTask-{i}",
            priority=TaskPriority.NORMAL
        )
    
    # Submit with different priorities
    await runtime.submit(
        quick_task, "Critical-1", name="CRITICAL", priority=TaskPriority.CRITICAL
    )
    await runtime.submit(
        quick_task, "Low-1", name="LOW", priority=TaskPriority.LOW
    )
    
    # Submit a failing task
    task_id = await runtime.submit(
        failing_task, name="FailingTask", max_retries=2
    )
    
    # Wait for completion
    print("[Waiting for tasks...]")
    await asyncio.sleep(3)
    
    # Stats
    print("\n[Stats]")
    stats = runtime.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # Stop
    await runtime.stop()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
