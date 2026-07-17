"""
SOLVENS SDK - Python API for AI Agent Orchestration

Example usage:
    from solvens import Cosmos, Agent, Provider
    
    # Define workflow
    cosmos = Cosmos("crm_generator")
    
    claude = Provider.anthropic(model="claude-3-5-sonnet")
    architect = Agent("architect", provider=claude)
    
    @cosmos.task(agent=architect)
    def design_api(spec: str) -> str:
        return f"Design API for: {spec}"
    
    # Run with simulation
    result = cosmos.run(simulate=True)
    print(result.outputs)
"""

__version__ = "1.0.0"
__author__ = "Luis Alberto Burciaga Miker"

from solvens.core import Cosmos, Agent, Provider, Task, WorkflowResult
from solvens.compiler import compile_cosmos, CosmosSyntaxError

__all__ = [
    "Cosmos",
    "Agent", 
    "Provider",
    "Task",
    "WorkflowResult",
    "compile_cosmos",
    "CosmosSyntaxError",
    "__version__",
]
