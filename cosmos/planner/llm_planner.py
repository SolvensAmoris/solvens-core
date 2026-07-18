"""
Cosmos LLM Planner

Uses LLM to decompose complex tasks into execution plans.
Minimal MVP - generates PlanNode DAG from natural language.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from .types import Plan, PlanNode, PlanStatus, StepStatus

logger = logging.getLogger("cosmos.planner")


# Default decomposition prompt
DECOMPOSITION_PROMPT = """You are a task planner. Decompose the following task into clear steps.

Task: {task}

Respond ONLY with valid JSON in this format:
{{
  "steps": [
    {{
      "name": "step_name",
      "description": "What this step does",
      "type": "task",
      "depends_on": ["previous_step_name"],
      "tools": ["tool_name"],
      "provider": "auto"
    }}
  ]
}}

Rules:
- First step has no depends_on
- Each step depends on the previous one unless parallel
- Keep steps atomic and actionable
- Maximum 10 steps
- Use simple step names (no spaces, lowercase)
- provider: "auto" for automatic selection, or "openai"/"anthropic"/"ollama"
- tools: list of tool names to use (optional, can be empty)
"""


class LLMPlanner:
    """
    LLM-based task planner.
    
    Uses LLM to decompose complex tasks into executable plans.
    Minimal MVP: generates PlanNode DAG from natural language.
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        prompt_template: str = DECOMPOSITION_PROMPT,
    ):
        """
        Initialize planner.
        
        Args:
            llm_client: Async LLM client (optional, uses mock if not provided)
            prompt_template: Template for decomposition prompt
        """
        self.llm_client = llm_client
        self.prompt_template = prompt_template
    
    async def create_plan(self, task: str) -> Plan:
        """
        Create execution plan from task description.
        
        Args:
            task: Natural language task description
            
        Returns:
            Plan with decomposed steps
        """
        logger.info(f"Creating plan for task: {task[:100]}...")
        start = time.time()
        
        # Generate steps using LLM
        steps_data = await self._generate_steps(task)
        
        # Build plan
        plan = Plan(task=task, status=PlanStatus.PENDING)
        
        # Create nodes
        for step_data in steps_data:
            node = PlanNode(
                name=step_data.get("name", f"step_{len(plan.nodes)}"),
                description=step_data.get("description", ""),
                step_type=step_data.get("type", "task"),
                dependencies=[],  # Will resolve by name
                provider=step_data.get("provider", "auto"),
                tools=step_data.get("tools", []),
            )
            plan.nodes.append(node)
        
        # Resolve dependencies by name
        self._resolve_dependencies(plan)
        
        # Mark initial nodes as ready
        plan.mark_ready()
        
        logger.info(f"Plan created: {len(plan.nodes)} steps in {(time.time()-start)*1000:.0f}ms")
        
        return plan
    
    async def _generate_steps(self, task: str) -> list[dict]:
        """
        Generate steps using LLM.
        
        Falls back to simple parsing if no LLM client.
        """
        if self.llm_client:
            return await self._llm_generate(task)
        else:
            return self._simple_parse(task)
    
    async def _llm_generate(self, task: str) -> list[dict]:
        """Generate steps using LLM."""
        prompt = self.prompt_template.format(task=task)
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_client.complete(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON from response
            steps = self._parse_steps_json(content)
            if steps:
                return steps
            
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}, falling back to simple parse")
        
        return self._simple_parse(task)
    
    def _parse_steps_json(self, content: str) -> Optional[list[dict]]:
        """Parse JSON from LLM response."""
        try:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                # Try raw JSON
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            data = json.loads(content)
            return data.get("steps", [])
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse steps JSON: {e}")
            return None
    
    def _simple_parse(self, task: str) -> list[dict]:
        """
        Simple fallback: create single step plan.
        
        Used when no LLM available.
        """
        # Detect task complexity by keywords
        task_lower = task.lower()
        
        steps = []
        
        # Check for multi-step indicators
        if any(kw in task_lower for kw in ["research", "analyze", "summarize", "compare", "review"]):
            # Multi-step task
            steps.append({
                "name": "research",
                "description": "Gather information and research the topic",
                "type": "task",
                "depends_on": [],
                "provider": "auto",
            })
            
            if any(kw in task_lower for kw in ["summarize", "report", "create", "write"]):
                steps.append({
                    "name": "synthesize",
                    "description": "Synthesize findings into output",
                    "type": "task",
                    "depends_on": ["research"],
                    "provider": "auto",
                })
            
            if any(kw in task_lower for kw in ["save", "store", "export"]):
                steps.append({
                    "name": "save",
                    "description": "Save results to storage",
                    "type": "tool",
                    "depends_on": ["synthesize"] if len(steps) > 1 else ["research"],
                    "provider": "auto",
                })
        else:
            # Simple task - single step
            steps.append({
                "name": "execute",
                "description": task[:100],
                "type": "task",
                "depends_on": [],
                "provider": "auto",
            })
        
        return steps if steps else [{"name": "execute", "description": task, "type": "task", "depends_on": []}]
    
    def _resolve_dependencies(self, plan: Plan) -> None:
        """Resolve dependencies by name to node IDs."""
        name_to_id = {node.name: node.id for node in plan.nodes}
        
        for node in plan.nodes:
            resolved_deps = []
            for dep_name in node.dependencies:
                if dep_name in name_to_id:
                    resolved_deps.append(name_to_id[dep_name])
            
            node.dependencies = resolved_deps


class MockLLMClient:
    """Mock LLM client for testing without API access."""
    
    async def complete(self, messages: list[dict]) -> Any:
        """Return mock completion."""
        class MockResponse:
            content = '{"steps": [{"name": "step1", "description": "Do thing", "type": "task", "depends_on": []}]}'
        
        return MockResponse()
