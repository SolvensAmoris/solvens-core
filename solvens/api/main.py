"""FastAPI REST API for SOLVENS CORE."""

from __future__ import annotations

import asyncio
import os
import structlog
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field

from solvens import __version__
from solvens.agents.orchestrator import AgentOrchestrator, OrchestratorConfig
from solvens.core.config import get_settings
from solvens.core.exceptions import SolvensError
from solvens.core.types import Message, MessageRole, TaskPriority, TaskStatus
from solvens.router import CapabilityRouter
from security.oidc import Principal, require_principal, require_role
from solvens.persistence.database import get_session_factory
from solvens.persistence.models import CoreTaskRecord


# === Request/Response Models ===

class ChatRequest(BaseModel):
    """Chat completion request."""
    messages: list[Message]
    model: str | None = None
    provider: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None


class ChatResponse(BaseModel):
    """Chat completion response."""
    content: str
    model: str
    usage: dict[str, int] | None = None


class TaskRequest(BaseModel):
    """Task creation request."""
    description: str = Field(min_length=1, max_length=10000)
    priority: TaskPriority = TaskPriority.NORMAL
    callback: str | None = None  # Arbitrary callbacks are not executed.
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=256)


class TaskResponse(BaseModel):
    """Task status response."""
    id: str
    description: str
    status: TaskStatus
    result: Any | None = None
    error: str | None = None


class ProviderInfo(BaseModel):
    """Provider information."""
    name: str
    type: str
    enabled: bool
    models: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime: float


# === Application Lifecycle ===

orchestrator: AgentOrchestrator | None = None
router: CapabilityRouter | None = None
start_time: float = 0
task_tenants: dict[str, str] = {}
task_users: dict[str, str] = {}
durable_mode: bool = False


async def _durable_echo(payload: dict[str, Any]) -> dict[str, str]:
    """Safe built-in durable handler used by the API task endpoint."""
    description = payload.get("description")
    if not isinstance(description, str):
        raise ValueError("description must be a string")
    return {"status": "completed", "message": f"Task: {description}"}


def _durable_task_status(value: str) -> TaskStatus:
    return {
        "queued": TaskStatus.PENDING,
        "pending": TaskStatus.PENDING,
        "running": TaskStatus.RUNNING,
        "completed": TaskStatus.COMPLETED,
        "failed": TaskStatus.FAILED,
        "cancel_requested": TaskStatus.CANCELLED,
        "cancelled": TaskStatus.CANCELLED,
    }.get(value, TaskStatus.FAILED)


def _durable_task_description(record: CoreTaskRecord) -> str:
    envelope = record.payload or {}
    input_payload = envelope.get("input", {})
    description = input_payload.get("description", "") if isinstance(input_payload, dict) else ""
    return description if isinstance(description, str) else ""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    global orchestrator, router, start_time, durable_mode
    import time
    start_time = time.time()
    
    # Initialize services
    database_configured = bool(os.getenv("SOLVENS_DATABASE_URL") or os.getenv("DATABASE_URL"))
    durable_mode = database_configured
    durable_workers = max(0, int(os.getenv("SOLVENS_DURABLE_WORKERS", "1"))) if database_configured else 0
    durable_lease_seconds = int(os.getenv("SOLVENS_DURABLE_LEASE_SECONDS", "60"))
    durable_poll_interval = float(os.getenv("SOLVENS_DURABLE_POLL_INTERVAL", "1.0"))
    orchestrator = AgentOrchestrator(
        OrchestratorConfig(
            durable_workers=durable_workers,
            durable_lease_seconds=durable_lease_seconds,
            durable_poll_interval=durable_poll_interval,
        )
    )
    if durable_workers:
        orchestrator.register_durable_handler("api.echo", _durable_echo)
    router = CapabilityRouter()
    
    await orchestrator.initialize()
    await router.initialize()
    
    logger.info("SOLVENS CORE API started")
    
    yield
    
    # Cleanup
    if orchestrator:
        await orchestrator.shutdown()
    if router:
        await router.shutdown()
    durable_mode = False
    task_tenants.clear()
    task_users.clear()
    orchestrator = None
    router = None
    
    logger.info("SOLVENS CORE API stopped")


# === Create App ===

logger = structlog.get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="SOLVENS CORE API",
    description="AI Operating System - Modular kernel for intelligent agents",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware

_cors_origins = [
    origin.strip()
    for origin in os.getenv("SOLVENS_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if "*" in _cors_origins:
    raise RuntimeError("Wildcard CORS origins are forbidden")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# === Routes ===

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Check API health status."""
    import time
    return HealthResponse(
        status="healthy",
        version=__version__,
        uptime=time.time() - start_time,
    )


@app.get("/status", tags=["System"])
async def get_status(principal: Principal = Depends(require_principal)) -> dict[str, Any]:
    """Get system status including orchestrator and router stats."""
    if not orchestrator or not router:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    return {
        "version": __version__,
        "orchestrator": orchestrator.stats,
        "router": router.routing_stats,
        "settings": {
            "app_name": settings.app_name,
            "debug": settings.debug,
        },
    }


# === Chat Routes ===

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, principal: Principal = Depends(require_principal)) -> ChatResponse:
    """Send a chat completion request.
    
    The request will be routed to the optimal provider based on content analysis.
    """
    require_role(principal, "developer", "editor", "admin", "owner")
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    try:
        content = await router.route(
            messages=request.messages,
            preferred_model=request.model,
            preferred_provider=request.provider,
        )
        
        return ChatResponse(
            content=content,
            model=request.model or "auto",
            usage=None,
        )
    except SolvensError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest, principal: Principal = Depends(require_principal)) -> StreamingResponse:
    """Stream a chat completion response.
    
    Note: Requires a provider that supports streaming.
    """
    require_role(principal, "developer", "editor", "admin", "owner")
    # TODO: Implement streaming
    raise HTTPException(status_code=501, detail="Streaming not yet implemented")


# === Task Routes ===

@app.post("/tasks", response_model=TaskResponse, tags=["Tasks"])
async def create_task(request: TaskRequest, principal: Principal = Depends(require_principal)) -> TaskResponse:
    """Persist a serializable task and return its durable task ID."""
    require_role(principal, "developer", "editor", "admin", "owner")
    if request.callback is not None:
        raise HTTPException(
            status_code=400,
            detail="Callback names are not accepted; use a server-registered durable handler",
        )
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    priority_values = {
        TaskPriority.LOW: 0,
        TaskPriority.NORMAL: 10,
        TaskPriority.HIGH: 20,
        TaskPriority.CRITICAL: 30,
    }
    if durable_mode:
        if not orchestrator.durable_enabled:
            raise HTTPException(status_code=503, detail="Durable task workers are disabled")
        if not principal.user_id:
            raise HTTPException(status_code=403, detail="Durable user identity required")
        try:
            task_id = await orchestrator.submit_durable_task(
                tenant_id=principal.tenant_id,
                user_id=principal.user_id,
                handler_name="api.echo",
                payload={"description": request.description},
                priority=priority_values[request.priority],
                idempotency_key=request.idempotency_key,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (SQLAlchemyError, RuntimeError) as exc:
            raise HTTPException(status_code=503, detail="Task database unavailable") from exc
        return TaskResponse(
            id=task_id,
            description=request.description,
            status=TaskStatus.PENDING,
        )

    # Local development/test fallback remains process-local when no DB is configured.
    async def dummy_callback():
        return {"status": "completed", "message": f"Task: {request.description}"}

    task_id = await orchestrator.submit_task(
        description=request.description,
        callback=dummy_callback,
        priority=request.priority,
    )
    task_tenants[task_id] = principal.tenant_id
    task_users[task_id] = principal.user_id or ""
    return TaskResponse(
        id=task_id,
        description=request.description,
        status=TaskStatus.PENDING,
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(task_id: str, principal: Principal = Depends(require_principal)) -> TaskResponse:
    """Get task status, scoped to the authenticated tenant and user."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if durable_mode:
        try:
            factory = get_session_factory()
            async with factory() as session:
                record = (
                    await session.execute(
                        select(CoreTaskRecord).where(
                            CoreTaskRecord.id == task_id,
                            CoreTaskRecord.tenant_id == principal.tenant_id,
                            CoreTaskRecord.user_id == principal.user_id,
                        )
                    )
                ).scalars().one_or_none()
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail="Task database unavailable") from exc
        if record is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskResponse(
            id=record.id,
            description=_durable_task_description(record),
            status=_durable_task_status(record.status),
            result=record.result,
            error=record.error,
        )

    if (
        task_tenants.get(task_id) != principal.tenant_id
        or task_users.get(task_id) != (principal.user_id or "")
    ):
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        task = orchestrator.get_task(task_id)
        return TaskResponse(
            id=task.id,
            description=task.description,
            status=task.status,
            result=task.result,
            error=task.error,
        )
    except SolvensError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tasks", response_model=list[TaskResponse], tags=["Tasks"])
async def list_tasks(
    status: TaskStatus | None = None,
    limit: int = 100,
    principal: Principal = Depends(require_principal),
) -> list[TaskResponse]:
    """List tasks scoped to the authenticated tenant and user."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    limit = max(1, min(limit, 1000))

    if durable_mode:
        try:
            factory = get_session_factory()
            async with factory() as session:
                statement = select(CoreTaskRecord).where(
                    CoreTaskRecord.tenant_id == principal.tenant_id,
                    CoreTaskRecord.user_id == principal.user_id,
                )
                if status is not None:
                    db_status = {
                        TaskStatus.PENDING: "queued",
                        TaskStatus.RUNNING: "running",
                        TaskStatus.COMPLETED: "completed",
                        TaskStatus.FAILED: "failed",
                        TaskStatus.CANCELLED: "cancelled",
                    }[status]
                    if status == TaskStatus.CANCELLED:
                        statement = statement.where(
                            CoreTaskRecord.status.in_(("cancelled", "cancel_requested"))
                        )
                    else:
                        statement = statement.where(CoreTaskRecord.status == db_status)
                records = (
                    await session.execute(
                        statement.order_by(CoreTaskRecord.created_at.desc()).limit(limit)
                    )
                ).scalars().all()
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail="Task database unavailable") from exc
        return [
            TaskResponse(
                id=record.id,
                description=_durable_task_description(record),
                status=_durable_task_status(record.status),
                result=record.result,
                error=record.error,
            )
            for record in records
        ]

    tasks = [
        task
        for task in orchestrator.list_tasks(status=status, limit=limit)
        if task_tenants.get(task.id) == principal.tenant_id
        and task_users.get(task.id) == (principal.user_id or "")
    ]
    return [
        TaskResponse(
            id=task.id,
            description=task.description,
            status=task.status,
            result=task.result,
            error=task.error,
        )
        for task in tasks
    ]


@app.delete("/tasks/{task_id}", tags=["Tasks"])
async def cancel_task(task_id: str, principal: Principal = Depends(require_principal)) -> dict[str, str]:
    """Cancel a queued task or request cancellation from its active lease owner."""
    require_role(principal, "developer", "editor", "admin", "owner")
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if durable_mode:
        if not orchestrator.durable_enabled:
            raise HTTPException(status_code=503, detail="Durable task workers are disabled")
        if not principal.user_id:
            raise HTTPException(status_code=403, detail="Durable user identity required")
        try:
            cancelled = await orchestrator.cancel_durable_task(
                task_id=task_id,
                tenant_id=principal.tenant_id,
                user_id=principal.user_id,
            )
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail="Task database unavailable") from exc
    else:
        if (
            task_tenants.get(task_id) != principal.tenant_id
            or task_users.get(task_id) != (principal.user_id or "")
        ):
            raise HTTPException(status_code=404, detail="Task not found")
        cancelled = await orchestrator.cancel_task(task_id)

    if not cancelled:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    return {"status": "cancellation_requested", "task_id": task_id}


# === Provider Routes ===

@app.get("/providers", response_model=list[ProviderInfo], tags=["Providers"])
async def list_providers(principal: Principal = Depends(require_principal)) -> list[ProviderInfo]:
    """List all available providers."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    providers = router._resource.list_providers()
    
    return [
        ProviderInfo(
            name=p.name,
            type=p.type.value,
            enabled=p.enabled,
            models=[m.id for m in p.models],
        )
        for p in providers
    ]


@app.get("/providers/{provider_type}/health", tags=["Providers"])
async def check_provider_health(provider_type: str, principal: Principal = Depends(require_principal)) -> dict[str, Any]:
    """Check if a specific provider is healthy."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    from solvens.core.types import ProviderType
    
    try:
        pt = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    provider = router._resource.get_provider(pt)
    
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {provider_type} not found")
    
    return {
        "provider": provider.name,
        "type": provider.type.value,
        "enabled": provider.enabled,
        "models_count": len(provider.models),
    }


# === Model Routes ===

@app.get("/models", tags=["Models"])
async def list_models(
    provider: str | None = None,
    capability: str | None = None,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """List available models."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    from solvens.core.types import ProviderType, ModelCapability
    
    provider_type = None
    if provider:
        try:
            provider_type = ProviderType(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
    
    cap = None
    if capability:
        try:
            cap = ModelCapability(capability)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capability: {capability}")
    
    models = router._resource.list_models(capability=cap, provider=provider_type)
    
    return {
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider.value,
                "capabilities": [c.value for c in m.capabilities],
                "max_tokens": m.max_tokens,
            }
            for m in models
        ],
        "total": len(models),
    }


# === Utility Routes ===

@app.post("/chat/parse", tags=["Utility"])
async def parse_messages(messages: list[dict[str, Any]], principal: Principal = Depends(require_principal)) -> list[Message]:
    """Parse raw message dicts into Message objects."""
    result = []
    for msg in messages:
        role = MessageRole(msg.get("role", "user"))
        content = msg.get("content", "")
        result.append(Message(role=role, content=content))
    return result


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "solvens.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
