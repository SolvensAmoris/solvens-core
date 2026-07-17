"""Base agent class for SOLVENS CORE."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from solvens.core.base import BaseModel
from solvens.core.types import Message, TaskPriority


@dataclass
class AgentConfig:
    """Configuration for an agent instance.
    
    Attributes:
        name: Agent name
        description: Agent description
        model: Model identifier to use
        provider: Provider to use (auto-selected if None)
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
        system_prompt: System prompt for the agent
        tools: List of available tools
    """
    
    name: str = "agent"
    description: str = ""
    model: str | None = None
    provider: str | None = None
    max_retries: int = 3
    timeout: int = 60
    system_prompt: str = ""
    tools: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Base class for all agents.
    
    Agents are autonomous entities that can execute tasks
    using AI models through providers.
    
    Attributes:
        config: Agent configuration
        id: Unique agent identifier
        created_at: Creation timestamp
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.id: str | None = None
        self.created_at = datetime.utcnow()
        self._messages: list[Message] = []

    @abstractmethod
    async def run(self, input: str | list[Message]) -> str:
        """Run the agent with given input.
        
        Args:
            input: User input string or message list
            
        Returns:
            Agent's response as string
        """
        ...

    @abstractmethod
    async def plan(self, task: str) -> list[str]:
        """Plan task decomposition.
        
        Args:
            task: Task to decompose
            
        Returns:
            List of subtasks
        """
        ...

    def add_message(self, message: Message) -> None:
        """Add a message to conversation history."""
        self._messages.append(message)

    def get_messages(self) -> list[Message]:
        """Get conversation history."""
        return self._messages.copy()

    def clear_messages(self) -> None:
        """Clear conversation history."""
        self._messages.clear()

    @property
    def name(self) -> str:
        """Get agent name."""
        return self.config.name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.config.name})>"


class SimpleAgent(Agent):
    """A simple agent implementation for basic tasks.
    
    This is a reference implementation that can be extended
    for more complex agent behaviors.
    """
    
    def __init__(self, config: AgentConfig, orchestrator: Any):
        super().__init__(config)
        self._orchestrator = orchestrator

    async def run(self, input: str | list[Message]) -> str:
        """Execute the agent with given input."""
        if isinstance(input, str):
            message = Message(role="user", content=input)
        else:
            message = input[-1] if input else Message(role="user", content="")

        self.add_message(message)
        
        # Route to provider via orchestrator
        response = await self._orchestrator.route_message(
            messages=self._messages,
            model=self.config.model,
            provider=self.config.provider,
        )
        
        self.add_message(Message(role="assistant", content=response))
        return response

    async def plan(self, task: str) -> list[str]:
        """Create a simple plan by breaking task into words."""
        # Simple decomposition - split by newlines or periods
        subtasks = [s.strip() for s in task.replace("\n", " ").split(".") if s.strip()]
        return subtasks if subtasks else [task]
