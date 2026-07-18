"""
Cosmos Planner - Types and Interfaces

MINIMAL MVP for task decomposition.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PlanStatus(Enum):
    """Status of a plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status of a step."""
    PENDING = "pending"
    WAITING = "waiting"  # Dependencies not met
    READY = "ready"  # Dependencies met
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanNode:
    """
    A node in the execution plan.
    
    Minimal representation - just id, type, inputs, outputs, deps, status.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    step_type: str = "task"  # task, agent, tool, condition
    inputs: dict[str, Any] = field(default_factory=dict)  # e.g., {"task": "original prompt"}
    outputs: dict[str, Any] = field(default_factory=dict)  # e.g., {"result": "..."}
    dependencies: list[str] = field(default_factory=list)  # IDs of nodes this depends on
    status: StepStatus = StepStatus.PENDING
    
    # Execution config
    provider: str = "auto"  # auto, openai, anthropic, ollama
    model: str = "auto"
    timeout: float = 60.0
    retry: int = 3
    tools: list[str] = field(default_factory=list)
    
    # Runtime state
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    @property
    def duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0
    
    @property
    def is_ready(self) -> bool:
        """Check if all dependencies are completed."""
        return self.status == StepStatus.READY


@dataclass
class Plan:
    """
    A complete execution plan.
    
    Contains DAG of steps with dependencies.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task: str = ""  # Original task description
    nodes: list[PlanNode] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Cost tracking
    total_cost: float = 0.0
    total_tokens: int = 0
    
    def get_node(self, node_id: str) -> Optional[PlanNode]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_ready_nodes(self) -> list[PlanNode]:
        """Get nodes that are ready to execute."""
        ready = []
        for node in self.nodes:
            if node.status != StepStatus.READY:
                continue
            # Check all dependencies are completed
            deps_completed = all(
                self.get_node(dep_id).status == StepStatus.COMPLETED
                for dep_id in node.dependencies
                if self.get_node(dep_id)
            )
            if deps_completed:
                ready.append(node)
        return ready
    
    def mark_ready(self) -> None:
        """Mark nodes as ready if their dependencies are met."""
        for node in self.nodes:
            if node.status != StepStatus.PENDING and node.status != StepStatus.WAITING:
                continue
            deps_completed = all(
                self.get_node(dep_id).status == StepStatus.COMPLETED
                for dep_id in node.dependencies
                if self.get_node(dep_id)
            )
            if deps_completed:
                node.status = StepStatus.READY
            elif node.dependencies and node.status == StepStatus.PENDING:
                node.status = StepStatus.WAITING
