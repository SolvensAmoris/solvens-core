"""FastAPI REST API for SOLVENS CORE."""

from __future__ import annotations

import asyncio
import structlog
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from solvens import __version__
from solvens.agents.orchestrator import AgentOrchestrator
from solvens.core.config import get_settings
from solvens.core.exceptions import SolvensError
from solvens.core.types import Message, MessageRole, TaskPriority, TaskStatus
from solvens.router import CapabilityRouter
from security.oidc import Principal, require_principal, require_role


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
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    callback: str | None = None  # For future: reference to callback


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    global orchestrator, router, start_time
    import time
    start_time = time.time()
    
    # Initialize services
    orchestrator = AgentOrchestrator()
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
import os

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
    """Create a new task.
    
    Tasks are queued and executed by the orchestrator.
    """
    require_role(principal, "developer", "editor", "admin", "owner")
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    async def dummy_callback():
        return {"status": "completed", "message": f"Task: {request.description}"}
    
    task_id = await orchestrator.submit_task(
        description=request.description,
        callback=dummy_callback,
        priority=request.priority,
    )
    
    task_tenants[task_id] = principal.tenant_id
    return TaskResponse(
        id=task_id,
        description=request.description,
        status=TaskStatus.PENDING,
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(task_id: str, principal: Principal = Depends(require_principal)) -> TaskResponse:
    """Get task status and result."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    if task_tenants.get(task_id) != principal.tenant_id:
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
    except SolvensError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/tasks", response_model=list[TaskResponse], tags=["Tasks"])
async def list_tasks(
    status: TaskStatus | None = None,
    limit: int = 100,
    principal: Principal = Depends(require_principal),
) -> list[TaskResponse]:
    """List tasks with optional status filter."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    tasks = [task for task in orchestrator.list_tasks(status=status, limit=limit)
             if task_tenants.get(task.id) == principal.tenant_id]
    
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
    """Cancel a running task."""
    require_role(principal, "developer", "editor", "admin", "owner")
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    if task_tenants.get(task_id) != principal.tenant_id:
        raise HTTPException(status_code=404, detail="Task not found")
    cancelled = await orchestrator.cancel_task(task_id)
    
    if not cancelled:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    
    return {"status": "cancelled", "task_id": task_id}


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
