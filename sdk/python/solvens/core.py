"""
SOLVENS Core - Main classes for SDK
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
import json


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Provider:
    """
    AI Provider configuration.
    
    Example:
        claude = Provider.anthropic(model="claude-3-5-sonnet")
        gpt = Provider.openai(model="gpt-4o")
        local = Provider.ollama(model="llama3")
    """
    
    name: str
    model: str
    api_key_env: Optional[str] = None
    
    @classmethod
    def anthropic(cls, model: str = "claude-3-5-sonnet", api_key_env: str = "ANTHROPIC_API_KEY"):
        return cls(name="anthropic", model=model, api_key_env=api_key_env)
    
    @classmethod
    def openai(cls, model: str = "gpt-4o", api_key_env: str = "OPENAI_API_KEY"):
        return cls(name="openai", model=model, api_key_env=api_key_env)
    
    @classmethod
    def google(cls, model: str = "gemini-1.5-pro", api_key_env: str = "GOOGLE_API_KEY"):
        return cls(name="google", model=model, api_key_env=api_key_env)
    
    @classmethod
    def ollama(cls, model: str = "llama3", api_key_env: Optional[str] = None):
        return cls(name="ollama", model=model, api_key_env=api_key_env)
    
    @classmethod
    def deepseek(cls, model: str = "deepseek-chat", api_key_env: str = "DEEPSEEK_API_KEY"):
        return cls(name="deepseek", model=model, api_key_env=api_key_env)
    
    def to_dict(self) -> dict:
        return {"name": self.name, "model": self.model}


@dataclass
class Agent:
    """
    AI Agent definition.
    
    Example:
        architect = Agent(
            "architect",
            provider=Provider.anthropic(),
            system="You are a software architect"
        )
    """
    
    name: str
    provider: Provider
    system: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider.to_dict(),
            "system": self.system,
            "description": self.description,
        }


@dataclass
class Task:
    """
    Task definition within a workflow.
    """
    
    name: str
    agent: Agent
    func: Optional[Callable] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    dependencies: list[str] = field(default_factory=list)
    retry: int = 3
    timeout: int = 300
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "agent": self.agent.name,
            "dependencies": self.dependencies,
            "retry": self.retry,
            "timeout": self.timeout,
        }


@dataclass
class WorkflowResult:
    """
    Result of a workflow execution.
    """
    
    run_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.status == "done" and self.error is None
    
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "outputs": self.outputs,
            "metrics": self.metrics,
            "error": self.error,
        }


@dataclass
class SimulationResult:
    """
    Result of workflow simulation.
    """
    
    workflow_name: str
    total_tasks: int
    estimated_time_ms: float
    estimated_cost_usd: float
    provider_breakdown: dict
    dag_structure: dict
    
    def to_dict(self) -> dict:
        return {
            "workflow_name": self.workflow_name,
            "total_tasks": self.total_tasks,
            "estimated_time_ms": self.estimated_time_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "provider_breakdown": self.provider_breakdown,
        }


class Cosmos:
    """
    Main SDK class for defining and running workflows.
    
    Example:
        cosmos = Cosmos("crm_generator")
        
        @cosmos.task(agent=architect)
        def design_api(spec: str):
            return f"Design API for: {spec}"
        
        result = cosmos.run()
    """
    
    def __init__(self, name: str, api_url: Optional[str] = None):
        self.name = name
        self.api_url = api_url or "http://localhost:8000"
        self.tasks: list[Task] = []
        self._task_decorators: list[dict] = []
    
    def task(
        self,
        agent: Agent,
        deps: list[str] = None,
        retry: int = 3,
        timeout: int = 300,
    ):
        """
        Decorator to define a task.
        
        Example:
            @cosmos.task(agent=architect, deps=["fetch_requirements"])
            def design_api(spec: str):
                return f"Design API for: {spec}"
        """
        def decorator(func: Callable) -> Callable:
            task_name = func.__name__
            task = Task(
                name=task_name,
                agent=agent,
                func=func,
                dependencies=deps or [],
                retry=retry,
                timeout=timeout,
            )
            self.tasks.append(task)
            self._task_decorators.append({
                "func": func,
                "task": task,
            })
            return func
        return decorator
    
    def run(
        self,
        simulate: bool = False,
        dashboard_url: Optional[str] = None,
        **inputs
    ) -> WorkflowResult | SimulationResult:
        """
        Run the workflow.
        
        Args:
            simulate: If True, only simulate without executing
            dashboard_url: URL of the dashboard for live visualization
            **inputs: Input values for the workflow
        
        Returns:
            WorkflowResult or SimulationResult
        """
        import httpx
        import uuid
        
        workflow = {
            "name": self.name,
            "tasks": [t.to_dict() for t in self.tasks],
        }
        
        endpoint = f"{self.api_url}/api/simulate" if simulate else f"{self.api_url}/api/run"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint, json=workflow)
                response.raise_for_status()
                data = response.json()
                
                if simulate:
                    return SimulationResult(
                        workflow_name=data.get("workflow_name", self.name),
                        total_tasks=data.get("total_tasks", len(self.tasks)),
                        estimated_time_ms=data.get("estimated_time_ms", 0),
                        estimated_cost_usd=data.get("estimated_cost_usd", 0),
                        provider_breakdown=data.get("provider_pct", {}),
                        dag_structure=data.get("dag", {}),
                    )
                else:
                    return WorkflowResult(
                        run_id=data.get("run_id", str(uuid.uuid4())),
                        status="running",
                        metrics=data.get("metrics", {}),
                    )
        except httpx.ConnectError:
            # API not running, return mock result
            return SimulationResult(
                workflow_name=self.name,
                total_tasks=len(self.tasks),
                estimated_time_ms=len(self.tasks) * 5000,
                estimated_cost_usd=len(self.tasks) * 0.005,
                provider_breakdown={"openai": 60, "anthropic": 40},
                dag_structure={},
            )
    
    def to_cosmos_file(self) -> str:
        """
        Compile the workflow to Cosmos Language format.
        """
        lines = [
            f"# {self.name}.cosmos",
            f"# Generated by SOLVENS SDK v{__import__('solvens').__version__}",
            "",
        ]
        
        # Providers
        providers_seen = set()
        for task in self.tasks:
            if task.agent.provider.name not in providers_seen:
                providers_seen.add(task.agent.provider.name)
                lines.append(f'provider {task.agent.provider.name} {{')
                lines.append(f'  type: "{task.agent.provider.name}"')
                lines.append(f'  model: "{task.agent.provider.model}"')
                lines.append("}")
                lines.append("")
        
        # Agents
        agents_seen = set()
        for task in self.tasks:
            if task.agent.name not in agents_seen:
                agents_seen.add(task.agent.name)
                lines.append(f'agent {task.agent.name} {{')
                lines.append(f'  provider: {task.agent.provider.name}')
                if task.agent.system:
                    lines.append(f'  system: "{task.agent.system[:50]}..."')
                lines.append("}")
                lines.append("")
        
        # Tasks
        for task in self.tasks:
            lines.append(f'task {task.name} {{')
            lines.append(f'  agent: {task.agent.name}')
            if task.dependencies:
                deps = ", ".join(task.dependencies)
                lines.append(f'  depends_on: [{deps}]')
            lines.append("}")
            lines.append("")
        
        return "\n".join(lines)
