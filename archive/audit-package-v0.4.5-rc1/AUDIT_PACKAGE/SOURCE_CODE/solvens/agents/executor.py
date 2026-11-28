"""Agent Executor - Handles agent execution logic."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import structlog

from solvens.core.exceptions import OrchestratorError
from solvens.core.types import Message, Response
from solvens.agents.base import Agent, AgentConfig

logger = structlog.get_logger(__name__)


class ExecutionContext:
    """Context for agent execution.
    
    Attributes:
        agent: The agent being executed
        messages: Conversation messages
        start_time: Execution start time
        metadata: Additional context metadata
    """
    
    def __init__(self, agent: Agent, messages: list[Message]):
        self.agent = agent
        self.messages = messages
        self.start_time = datetime.utcnow()
        self.metadata: dict[str, Any] = {}
        
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()


class AgentExecutor:
    """Executes agents with proper lifecycle management.
    
    Handles the execution of agent tasks, including:
    - Message preparation
    - Response handling
    - Error recovery
    - Timeout management
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 60,
        retry_delay: float = 1.0,
    ):
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_delay = retry_delay
        self._running: set[str] = set()

    async def execute(
        self,
        agent: Agent,
        messages: list[Message],
        retry: bool = True,
    ) -> Response:
        """Execute an agent with given messages.
        
        Args:
            agent: Agent to execute
            messages: Conversation messages
            retry: Whether to retry on failure
            
        Returns:
            Response from the agent
            
        Raises:
            OrchestratorError: If execution fails after retries
        """
        if agent.id in self._running:
            raise OrchestratorError(f"Agent {agent.id} is already running")
        
        self._running.add(agent.id)
        context = ExecutionContext(agent, messages)
        
        try:
            for attempt in range(self.max_retries if retry else 1):
                try:
                    result = await asyncio.wait_for(
                        agent.run(messages),
                        timeout=self.timeout,
                    )
                    
                    return Response(
                        content=result,
                        model=agent.config.model or "unknown",
                        finish_reason="stop",
                    )
                    
                except asyncio.TimeoutError:
                    logger.warning(
                        "Agent execution timeout",
                        agent=agent.name,
                        attempt=attempt + 1,
                        timeout=self.timeout,
                    )
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    
                    raise OrchestratorError(
                        f"Agent execution timed out after {self.max_retries} attempts"
                    )
                    
                except Exception as e:
                    logger.error(
                        "Agent execution error",
                        agent=agent.name,
                        error=str(e),
                        attempt=attempt + 1,
                    )
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    
                    raise OrchestratorError(f"Agent execution failed: {e}")
                    
        finally:
            self._running.discard(agent.id)
            logger.info(
                "Agent execution completed",
                agent=agent.name,
                elapsed=context.elapsed,
            )

    async def execute_stream(
        self,
        agent: Agent,
        messages: list[Message],
    ) -> Any:
        """Execute an agent with streaming response.
        
        Args:
            agent: Agent to execute
            messages: Conversation messages
            
        Yields:
            Response chunks as they arrive
        """
        if agent.id in self._running:
            raise OrchestratorError(f"Agent {agent.id} is already running")
        
        self._running.add(agent.id)
        
        try:
            async for chunk in agent.run_stream(messages):
                yield chunk
        finally:
            self._running.discard(agent.id)

    async def batch_execute(
        self,
        agent: Agent,
        messages_list: list[list[Message]],
        max_concurrent: int = 5,
    ) -> list[Response]:
        """Execute multiple agent tasks concurrently.
        
        Args:
            agent: Agent to use
            messages_list: List of message sets
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List of responses
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_limit(messages: list[Message]) -> Response:
            async with semaphore:
                return await self.execute(agent, messages, retry=False)
        
        tasks = [execute_with_limit(messages) for messages in messages_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                responses.append(Response(
                    content="",
                    model=agent.config.model or "unknown",
                    metadata={"error": str(result), "index": i},
                ))
            else:
                responses.append(result)
        
        return responses

    @property
    def is_running(self) -> bool:
        """Check if executor has running agents."""
        return len(self._running) > 0

    @property
    def running_count(self) -> int:
        """Get count of running agents."""
        return len(self._running)
