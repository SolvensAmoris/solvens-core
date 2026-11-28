"""
SOLVENS CORE Dashboard API

FastAPI + WebSockets for real-time DAG visualization.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from security.oidc import Principal, require_principal, require_role
from solvens.persistence.database import get_session_factory
from solvens.persistence.models import DashboardRunRecord, WebSocketTicketRecord


# ============================================================================
# Models
# ============================================================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class WSMessageType(str, Enum):
    TASK_START = "task_start"
    TASK_END = "task_end"
    TASK_ERROR = "task_error"
    METRIC_UPDATE = "metric_update"
    RUN_START = "run_start"
    RUN_END = "run_end"
    DAG_UPDATE = "dag_update"


@dataclass
class TaskNode:
    id: str
    name: str
    provider: str
    model: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


@dataclass
class RunMetrics:
    total_time_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    parallelism: int = 0
    reuse_pct: float = 0.0
    tasks_completed: int = 0
    tasks_total: int = 0
    provider_breakdown: dict = field(default_factory=dict)


@dataclass
class RunState:
    run_id: str
    workflow_name: str
    tenant_id: str
    user_id: str | None = None
    status: str = "pending"
    tasks: dict[str, TaskNode] = field(default_factory=dict)
    metrics: RunMetrics = field(default_factory=RunMetrics)
    created_at: float = field(default_factory=time.time)
    estimated_time_ms: float = 0.0
    estimated_cost_usd: float = 0.0


@dataclass
class WSMessage:
    type: WSMessageType
    data: dict
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp
        })


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections per run."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, message: WSMessage):
        if run_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_text(message.to_json())
                except:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn, run_id)


manager = ConnectionManager()
logger = logging.getLogger(__name__)

# ============================================================================
# Run Storage
# ============================================================================

runs: dict[str, RunState] = {}
ws_tickets: dict[str, tuple[Principal, float]] = {}  # legacy test hook; never stores live tickets


class WsTicketRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)


def _serialize_run(run: RunState) -> dict:
    return {
        "run_id": run.run_id,
        "workflow_name": run.workflow_name,
        "tenant_id": run.tenant_id,
        "user_id": run.user_id,
        "status": run.status,
        "tasks": {
            task_id: {
                "id": task.id,
                "name": task.name,
                "provider": task.provider,
                "model": task.model,
                "status": task.status.value,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "input_tokens": task.input_tokens,
                "output_tokens": task.output_tokens,
                "cost_usd": task.cost_usd,
                "dependencies": list(task.dependencies),
                "logs": list(task.logs),
            }
            for task_id, task in run.tasks.items()
        },
        "metrics": asdict(run.metrics),
        "created_at": run.created_at,
        "estimated_time_ms": run.estimated_time_ms,
        "estimated_cost_usd": run.estimated_cost_usd,
    }


def _deserialize_run(record: DashboardRunRecord) -> RunState:
    snapshot = record.snapshot if isinstance(record.snapshot, dict) else {}
    tasks: dict[str, TaskNode] = {}
    raw_tasks = snapshot.get("tasks", {})
    if isinstance(raw_tasks, dict):
        for task_id, raw in raw_tasks.items():
            if not isinstance(raw, dict):
                continue
            try:
                task_status = TaskStatus(raw.get("status", "pending"))
            except ValueError:
                task_status = TaskStatus.ERROR
            tasks[str(task_id)] = TaskNode(
                id=str(raw.get("id", task_id)),
                name=str(raw.get("name", task_id)),
                provider=str(raw.get("provider", "unknown")),
                model=str(raw.get("model", "default")),
                status=task_status,
                start_time=raw.get("start_time"),
                end_time=raw.get("end_time"),
                input_tokens=int(raw.get("input_tokens", 0)),
                output_tokens=int(raw.get("output_tokens", 0)),
                cost_usd=float(raw.get("cost_usd", 0.0)),
                dependencies=list(raw.get("dependencies", [])),
                logs=list(raw.get("logs", [])),
            )
    raw_metrics = snapshot.get("metrics", {})
    if not isinstance(raw_metrics, dict):
        raw_metrics = {}
    metric_fields = RunMetrics.__dataclass_fields__.keys()
    metrics = RunMetrics(**{key: value for key, value in raw_metrics.items() if key in metric_fields})
    created_at = snapshot.get("created_at")
    if not isinstance(created_at, (int, float)):
        created_at = record.created_at.timestamp()
    return RunState(
        run_id=record.id,
        workflow_name=record.workflow_name,
        tenant_id=record.tenant_id,
        user_id=record.user_id,
        status=record.status,
        tasks=tasks,
        metrics=metrics,
        created_at=float(created_at),
        estimated_time_ms=float(snapshot.get("estimated_time_ms", 0.0)),
        estimated_cost_usd=float(snapshot.get("estimated_cost_usd", 0.0)),
    )


async def _persist_run(run: RunState, *, create: bool = False) -> None:
    if not run.user_id:
        raise ValueError("Run requires a durable internal user ID")
    snapshot = _serialize_run(run)
    json.dumps(snapshot, allow_nan=False)
    factory = get_session_factory()
    async with factory() as session:
        record = (
            await session.execute(
                select(DashboardRunRecord)
                .where(DashboardRunRecord.id == run.run_id)
                .with_for_update()
            )
        ).scalars().one_or_none()
        if record is None:
            if not create:
                raise LookupError("Dashboard run record not found")
            record = DashboardRunRecord(
                id=run.run_id,
                tenant_id=run.tenant_id,
                user_id=run.user_id,
                workflow_name=run.workflow_name,
                status=run.status,
                snapshot=snapshot,
                sequence=1,
            )
            session.add(record)
        else:
            if record.tenant_id != run.tenant_id or record.user_id != run.user_id:
                raise PermissionError("Dashboard run owner mismatch")
            record.status = run.status
            record.snapshot = snapshot
            record.sequence += 1
        await session.commit()


async def _load_run_record(
    run_id: str, *, tenant_id: str, user_id: str
) -> DashboardRunRecord | None:
    factory = get_session_factory()
    async with factory() as session:
        return (
            await session.execute(
                select(DashboardRunRecord).where(
                    DashboardRunRecord.id == run_id,
                    DashboardRunRecord.tenant_id == tenant_id,
                    DashboardRunRecord.user_id == user_id,
                )
            )
        ).scalars().one_or_none()


async def _consume_ws_ticket(ticket: str, run_id: str) -> tuple[str, str] | None:
    if not ticket or len(ticket) > 512:
        return None
    ticket_hash = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    factory = get_session_factory()
    async with factory() as session:
        record = (
            await session.execute(
                select(WebSocketTicketRecord)
                .where(
                    WebSocketTicketRecord.ticket_hash == ticket_hash,
                    WebSocketTicketRecord.run_id == run_id,
                    WebSocketTicketRecord.consumed_at.is_(None),
                    WebSocketTicketRecord.expires_at > now,
                )
                .with_for_update(skip_locked=True)
            )
        ).scalars().one_or_none()
        if record is None:
            await session.rollback()
            return None
        record.consumed_at = now
        await session.commit()
        return record.tenant_id, record.user_id


def _run_to_dag(run: RunState) -> dict:
    nodes = []
    for task in run.tasks.values():
        nodes.append({
            "id": task.id,
            "type": "task",
            "data": {
                "label": task.name,
                "provider": task.provider,
                "model": task.model,
                "status": task.status.value,
                "cost_usd": task.cost_usd,
                "tokens": task.input_tokens + task.output_tokens,
            },
        })
    edges = [
        {"source": dependency, "target": task.id, "type": "default"}
        for task in run.tasks.values()
        for dependency in task.dependencies
    ]
    return {
        "run_id": run.run_id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "nodes": nodes,
        "edges": edges,
        "metrics": asdict(run.metrics),
        "estimated_time_ms": run.estimated_time_ms,
        "estimated_cost_usd": run.estimated_cost_usd,
    }


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="SOLVENS CORE Dashboard API",
    description="Real-time DAG execution dashboard",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_cors_origins = [origin.strip() for origin in os.getenv("SOLVENS_CORS_ORIGINS", "").split(",") if origin.strip()]
if "*" in _cors_origins:
    raise RuntimeError("Wildcard CORS origins are forbidden")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/run/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, ticket: str = Query(...)):
    """Consume a hashed, run-bound ticket once and load the durable run snapshot."""
    try:
        owner = await _consume_ws_ticket(ticket, run_id)
    except (SQLAlchemyError, RuntimeError):
        await websocket.close(code=1011)
        return
    if owner is None:
        await websocket.close(code=4401)
        return

    tenant_id, user_id = owner
    try:
        record = await _load_run_record(
            run_id, tenant_id=tenant_id, user_id=user_id
        )
    except (SQLAlchemyError, RuntimeError):
        await websocket.close(code=1011)
        return
    if record is None:
        await websocket.close(code=4404)
        return

    run = runs.get(run_id)
    if run is None or run.tenant_id != tenant_id or run.user_id != user_id:
        run = _deserialize_run(record)
        runs[run_id] = run

    await manager.connect(websocket, run_id)
    try:
        await websocket.send_text(json.dumps({
            "type": "dag_update",
            "data": _run_to_dag(run),
            "timestamp": time.time(),
        }))
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": time.time(),
                    }))
            except (json.JSONDecodeError, AttributeError):
                continue
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)
    except Exception:
        logger.exception("Dashboard WebSocket failed", extra={"run_id": run_id})
        manager.disconnect(websocket, run_id)


# ============================================================================
# REST Endpoints
# ============================================================================

@app.post("/api/auth/ws-ticket")
async def create_ws_ticket(
    request: WsTicketRequest,
    principal: Principal = Depends(require_principal),
):
    """Issue a run-bound one-use ticket; only its hash is stored."""
    if not principal.user_id:
        raise HTTPException(status_code=403, detail="Durable user identity required")
    now = datetime.now(timezone.utc)
    ticket = secrets.token_urlsafe(32)
    ticket_hash = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
    factory = get_session_factory()
    try:
        async with factory() as session:
            run = (
                await session.execute(
                    select(DashboardRunRecord).where(
                        DashboardRunRecord.id == request.run_id,
                        DashboardRunRecord.tenant_id == principal.tenant_id,
                        DashboardRunRecord.user_id == principal.user_id,
                    )
                )
            ).scalars().one_or_none()
            if run is None:
                raise HTTPException(status_code=404, detail="Run not found")
            await session.execute(
                delete(WebSocketTicketRecord).where(
                    WebSocketTicketRecord.expires_at <= now
                )
            )
            session.add(WebSocketTicketRecord(
                ticket_hash=ticket_hash,
                user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                run_id=request.run_id,
                expires_at=now + timedelta(seconds=30),
            ))
            await session.commit()
    except HTTPException:
        raise
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Ticket database unavailable") from exc
    return {"ticket": ticket, "expires_in": 30}


@app.get("/api/runs")
async def list_runs(principal: Principal = Depends(require_principal)):
    """List durable runs owned by the authenticated user and tenant."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            records = (
                await session.execute(
                    select(DashboardRunRecord)
                    .where(
                        DashboardRunRecord.tenant_id == principal.tenant_id,
                        DashboardRunRecord.user_id == principal.user_id,
                    )
                    .order_by(DashboardRunRecord.created_at.desc())
                    .limit(100)
                )
            ).scalars().all()
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Run database unavailable") from exc

    response = []
    for record in records:
        snapshot = record.snapshot if isinstance(record.snapshot, dict) else {}
        metrics = snapshot.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        response.append({
            "run_id": record.id,
            "workflow_name": record.workflow_name,
            "status": record.status,
            "tasks_completed": metrics.get("tasks_completed", 0),
            "tasks_total": metrics.get("tasks_total", 0),
            "created_at": created_at.timestamp(),
        })
    return response


@app.get("/api/run/{run_id}")
async def get_run(run_id: str, principal: Principal = Depends(require_principal)):
    """Get a persisted run snapshot, scoped to its owner."""
    try:
        record = await _load_run_record(
            run_id, tenant_id=principal.tenant_id, user_id=principal.user_id or ""
        )
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Run database unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run = runs.get(run_id)
    if run is None or run.tenant_id != principal.tenant_id or run.user_id != principal.user_id:
        run = _deserialize_run(record)
        runs[run_id] = run
    return _run_to_dag(run)


@app.get("/api/run/{run_id}/metrics")
async def get_run_metrics(run_id: str, principal: Principal = Depends(require_principal)):
    """Get persisted run metrics, scoped to its owner."""
    try:
        record = await _load_run_record(
            run_id, tenant_id=principal.tenant_id, user_id=principal.user_id or ""
        )
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Run database unavailable") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run = runs.get(run_id)
    if run is None or run.tenant_id != principal.tenant_id or run.user_id != principal.user_id:
        run = _deserialize_run(record)
        runs[run_id] = run
    return asdict(run.metrics)


@app.post("/api/simulate")
async def simulate_workflow(workflow: dict, principal: Principal = Depends(require_principal)):
    """
    Simulate a workflow and return estimated metrics.
    """
    require_role(principal, "developer", "editor", "admin", "owner")
    workflow_name = workflow.get("name", "unnamed")
    tasks = workflow.get("tasks", [])

    # Parse tasks to build DAG
    dag_nodes = []
    dag_edges = []
    providers = {"anthropic": 0, "openai": 0, "google": 0, "ollama": 0, "deepseek": 0}

    for task in tasks:
        task_name = task.get("name", f"task_{len(dag_nodes)}")
        provider = task.get("provider", "openai").lower().replace('"', '')

        # Count by provider
        if "claude" in provider or "anthropic" in provider:
            providers["anthropic"] += 1
        elif "gpt" in provider or "openai" in provider:
            providers["openai"] += 1
        elif "gemini" in provider or "google" in provider:
            providers["google"] += 1
        elif "ollama" in provider or "local" in provider:
            providers["ollama"] += 1
        else:
            providers["deepseek"] += 1

        # Estimate cost based on provider
        if "claude" in provider:
            cost = 0.0035 * 5000  # Claude per 1K tokens estimate
        elif "ollama" in provider:
            cost = 0.0  # Free
        else:
            cost = 0.0020 * 5000  # Default estimate

        dag_nodes.append({
            "id": task_name,
            "type": "task",
            "data": {
                "label": task_name,
                "provider": provider,
                "status": "pending",
                "estimated_cost": cost
            }
        })

        # Add dependencies as edges
        deps = task.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        for dep in deps:
            dag_edges.append({
                "source": dep,
                "target": task_name,
                "type": "default"
            })

    # Calculate totals
    total_tasks = len(dag_nodes)
    parallel_groups = calculate_parallel_groups(dag_edges, total_tasks)
    estimated_time_ms = parallel_groups * 5000  # 5s per parallel group
    estimated_cost = sum(n["data"]["estimated_cost"] for n in dag_nodes)

    # Provider breakdown
    provider_pct = {k: round(v / total_tasks * 100, 1) for k, v in providers.items() if v > 0}

    return {
        "workflow_name": workflow_name,
        "total_tasks": total_tasks,
        "estimated_time_ms": estimated_time_ms,
        "estimated_cost_usd": estimated_cost,
        "parallel_groups": parallel_groups,
        "dag": {
            "nodes": dag_nodes,
            "edges": dag_edges
        },
        "providers": providers,
        "provider_pct": provider_pct,
        "message": f"{total_tasks} tasks in {parallel_groups} parallel groups"
    }


@app.post("/api/run")
async def start_run(workflow: dict, principal: Principal = Depends(require_principal)):
    """
    Start a new run and return run_id.
    """
    require_role(principal, "developer", "editor", "admin", "owner")
    if not principal.user_id:
        raise HTTPException(status_code=403, detail="Durable user identity required")
    run_id = str(uuid.uuid4())
    workflow_name = workflow.get("name", "unnamed")
    tasks = workflow.get("tasks", [])

    # Build DAG
    dag_nodes = {}
    dag_edges = []

    for task in tasks:
        task_name = task.get("name", f"task_{len(dag_nodes)}")
        provider = task.get("provider", "openai").lower().replace('"', '')
        deps = task.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]

        dag_nodes[task_name] = TaskNode(
            id=task_name,
            name=task_name,
            provider=provider,
            model="default",
            dependencies=deps
        )

        for dep in deps:
            dag_edges.append((dep, task_name))

    # Calculate estimates
    parallel_groups = calculate_parallel_groups(dag_edges, len(dag_nodes))
    estimated_time_ms = parallel_groups * 5000
    estimated_cost_usd = len(dag_nodes) * 0.005

    # Create and persist run state before announcing or executing it.
    run = RunState(
        run_id=run_id,
        workflow_name=workflow_name,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        tasks=dag_nodes,
        estimated_time_ms=estimated_time_ms,
        estimated_cost_usd=estimated_cost_usd,
    )
    run.metrics.tasks_total = len(dag_nodes)
    try:
        await _persist_run(run, create=True)
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Run database unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    runs[run_id] = run

    # Broadcast run start
    await manager.broadcast(run_id, WSMessage(
        type=WSMessageType.RUN_START,
        data={
            "run_id": run_id,
            "workflow_name": workflow_name,
            "tasks_total": len(dag_nodes),
            "estimated_time_ms": estimated_time_ms,
            "estimated_cost_usd": estimated_cost_usd
        }
    ))

    # Start async execution
    asyncio.create_task(execute_run(run_id, dag_nodes, dag_edges))

    return {"run_id": run_id, "status": "started"}


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_parallel_groups(edges: list, total_nodes: int) -> int:
    """Calculate number of parallel execution groups."""
    if not edges:
        return total_nodes

    # Simple heuristic: sqrt(total) parallel groups
    return max(1, int(total_nodes ** 0.5))


def get_run_dag(run_id: str) -> dict:
    """Get DAG representation of a run."""
    run = runs[run_id]

    nodes = []
    for task in run.tasks.values():
        nodes.append({
            "id": task.id,
            "type": "task",
            "data": {
                "label": task.name,
                "provider": task.provider,
                "model": task.model,
                "status": task.status.value,
                "cost_usd": task.cost_usd,
                "tokens": task.input_tokens + task.output_tokens
            }
        })

    edges = []
    for task in run.tasks.values():
        for dep in task.dependencies:
            edges.append({
                "source": dep,
                "target": task.id,
                "type": "default"
            })

    return {
        "run_id": run_id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "nodes": nodes,
        "edges": edges,
        "metrics": asdict(run.metrics),
        "estimated_time_ms": run.estimated_time_ms,
        "estimated_cost_usd": run.estimated_cost_usd
    }


async def execute_run(run_id: str, dag_nodes: dict, dag_edges: list):
    """Execute a run and broadcast events."""
    run = runs[run_id]
    run.status = "running"

    # Simple topological sort execution
    completed = set()
    pending = set(dag_nodes.keys())

    while pending:
        # Find tasks with all dependencies completed
        ready = []
        for task_id in pending:
            deps = dag_nodes[task_id].dependencies
            if all(d in completed for d in deps):
                ready.append(task_id)

        if not ready:
            # Deadlock or all blocked
            break

        # Execute ready tasks in parallel
        for task_id in ready:
            task = dag_nodes[task_id]

            # Broadcast task start
            await manager.broadcast(run_id, WSMessage(
                type=WSMessageType.TASK_START,
                data={
                    "task": task_id,
                    "provider": task.provider,
                    "model": task.model
                }
            ))

            # Update state
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()
            run.metrics.parallelism = len(ready)

            # Simulate execution (replace with actual execution)
            await asyncio.sleep(0.5)  # Simulated delay

            # Complete task
            task.status = TaskStatus.DONE
            task.end_time = time.time()
            task.output_tokens = 1000
            task.cost_usd = 0.002
            pending.remove(task_id)
            completed.add(task_id)

            # Update metrics
            run.metrics.tasks_completed += 1
            run.metrics.total_cost_usd += task.cost_usd
            run.metrics.total_tokens += task.input_tokens + task.output_tokens

            # Broadcast task end
            await manager.broadcast(run_id, WSMessage(
                type=WSMessageType.TASK_END,
                data={
                    "task": task_id,
                    "tokens": task.input_tokens + task.output_tokens,
                    "cost_usd": task.cost_usd,
                    "duration_ms": (task.end_time - task.start_time) * 1000
                }
            ))

            # Broadcast metric update
            await manager.broadcast(run_id, WSMessage(
                type=WSMessageType.METRIC_UPDATE,
                data=asdict(run.metrics)
            ))

    # Run complete
    run.status = "completed"
    run.metrics.total_time_ms = (time.time() - run.created_at) * 1000

    await manager.broadcast(run_id, WSMessage(
        type=WSMessageType.RUN_END,
        data={
            "run_id": run_id,
            "status": "completed",
            "total_time_ms": run.metrics.total_time_ms,
            "total_cost_usd": run.metrics.total_cost_usd
        }
    ))


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health():
    return {"status": "ok", "active_runs": len(runs)}


@app.get("/")
async def root():
    return {
        "name": "SOLVENS CORE Dashboard API",
        "version": "1.0.0",
        "docs": "/docs"
    }
