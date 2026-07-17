# SOLVENS SDK - Python

Python SDK for SOLVENS - AI Agent Orchestration Platform.

## Installation

```bash
pip install solvens
```

## Quick Start

```python
from solvens import Cosmos, Agent, Provider

# Define workflow
cosmos = Cosmos("crm_generator")

claude = Provider.anthropic(model="claude-3-5-sonnet")
architect = Agent("architect", provider=claude)

@cosmos.task(agent=architect)
def design_api(spec: str) -> str:
    return f"Design API for: {spec}"

# Simulate first
result = cosmos.run(simulate=True)
print(f"Estimated cost: ${result.estimated_cost_usd:.4f}")

# Run
result = cosmos.run()
print(result.outputs)
```

## CLI

```bash
# Initialize project
solvens init my-project
cd my-project

# Simulate workflow
solvens simulate workflows/main.cosmos

# Run workflow
solvens run workflows/main.cosmos

# Validate
solvens validate workflows/main.cosmos

# Deploy
solvens deploy workflows/main.cosmos --public
```

## Cosmos Language

```cosmos
provider claude {
  type: "anthropic"
  model: "claude-3-5-sonnet"
}

agent architect {
  provider: claude
  system: "You are a software architect"
}

task design_api {
  agent: architect
  depends_on: [fetch_requirements]
}
```

## Features

- 🌌 **DAG Visualization** - See your workflow as a graph
- 🔮 **Pre-execution Simulation** - Know cost before running
- 📊 **Real-time Metrics** - Track cost, tokens, parallelism
- 🔄 **Multi-provider Routing** - OpenAI, Claude, Gemini, Ollama
- 📦 **Cosmos Hub** - Share and reuse workflows

## Documentation

Full documentation at [docs.solvens.amoris](https://docs.solvens.amoris)

## Author

Luis Alberto Burciaga Miker  
https://github.com/SolvensAmoris/solvens-core
