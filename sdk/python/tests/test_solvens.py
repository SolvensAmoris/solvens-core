"""
Tests for SOLVENS SDK
"""

import pytest
from solvens.core import Provider, Agent, Task, Cosmos, WorkflowResult, SimulationResult
from solvens.compiler import compile_cosmos, decompile_cosmos


class TestProvider:
    """Tests for Provider class."""
    
    def test_anthropic(self):
        p = Provider.anthropic()
        assert p.name == "anthropic"
        assert p.model == "claude-3-5-sonnet"
    
    def test_openai(self):
        p = Provider.openai(model="gpt-4o")
        assert p.name == "openai"
        assert p.model == "gpt-4o"


class TestAgent:
    """Tests for Agent class."""
    
    def test_create_agent(self):
        provider = Provider.anthropic()
        agent = Agent("architect", provider=provider)
        assert agent.name == "architect"
        assert agent.provider.name == "anthropic"


class TestCosmos:
    """Tests for Cosmos workflow class."""
    
    def test_create_workflow(self):
        cosmos = Cosmos("test_workflow")
        assert cosmos.name == "test_workflow"
        assert len(cosmos.tasks) == 0
    
    def test_add_task(self):
        cosmos = Cosmos("test_workflow")
        agent = Agent("test", provider=Provider.anthropic())
        
        @cosmos.task(agent=agent)
        def my_task():
            pass
        
        assert len(cosmos.tasks) == 1
        assert cosmos.tasks[0].name == "my_task"


class TestCompiler:
    """Tests for Cosmos language compiler."""
    
    def test_compile_simple(self):
        source = '''
provider openai {
  type: "openai"
  model: "gpt-4o"
}

agent assistant {
  provider: openai
}

task greet {
  agent: assistant
}
'''
        result = compile_cosmos(source)
        assert len(result["providers"]) == 1
        assert len(result["agents"]) == 1
        assert len(result["tasks"]) == 1
    
    def test_decompile(self):
        data = {
            "providers": [{"name": "openai", "type": "openai"}],
            "agents": [],
            "tasks": [{"name": "greet", "agent": "assistant"}],
            "dags": [],
        }
        
        source = decompile_cosmos(data)
        assert "provider openai" in source
        assert "task greet" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
