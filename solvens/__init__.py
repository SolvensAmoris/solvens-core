"""
Solvens Core v0.2 - AI Operating System Kernel
=============================================

El kernel que no pide permiso.
Agentes que orquestan, routan por plata, ejecutan en Cosmos DAG y facturan solos.

Usage:
    from solvens import Runtime, SmartRouter, SelfBillingAgent
    
    # Launch revenue agent
    solvens launch revenue
    
    # Battle providers
    solvens battle grok claude

Author: Luis Alberto Burciaga Miker
"""

__version__ = "0.2.0"
__author__ = "Luis Alberto Burciaga Miker"
__license__ = "MIT"

# Core exports
from solvens.runtime.orchestrator import (
    RuntimeOrchestrator,
    Task,
    TaskPriority,
    TaskStatus,
    get_runtime,
    init_runtime,
    shutdown_runtime,
)

from solvens.router.smart_router import (
    SmartRouter,
    ProviderType,
    TaskType,
    get_router,
)

from solvens.plugins.revenue.self_billing_agent import (
    SelfBillingAgent,
    AgentConfig,
    BillingDatabase,
)

__all__ = [
    # Version
    "__version__",
    # Runtime
    "RuntimeOrchestrator",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "get_runtime",
    "init_runtime",
    "shutdown_runtime",
    # Router
    "SmartRouter",
    "ProviderType",
    "TaskType",
    "get_router",
    # Billing
    "SelfBillingAgent",
    "AgentConfig",
    "BillingDatabase",
]
