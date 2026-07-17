# SOLVENS SDK

SDKs for SOLVENS - AI Agent Orchestration Platform.

## Structure

```
sdk/
├── python/           # Python SDK (pip install solvens)
│   ├── solvens/     # Core package
│   └── pyproject.toml
└── typescript/      # TypeScript SDK (npm install solvens)
    └── src/
```

## Python SDK

```bash
pip install solvens
```

### Quick Start

```python
from solvens import Cosmos, Agent, Provider

cosmos = Cosmos("my_workflow")

claude = Provider.anthropic(model="claude-3-5-sonnet")
architect = Agent("architect", provider=claude)

@cosmos.task(agent=architect)
def design_api(spec: str):
    return f"Design API for: {spec}"

# Simulate
result = cosmos.run(simulate=True)
print(f"Cost: ${result.estimated_cost_usd:.4f}")

# Run
result = cosmos.run()
```

### CLI

```bash
solvens init my-project
solvens run workflows/main.cosmos
solvens simulate workflows/main.cosmos
solvens deploy workflows/main.cosmos
```

## TypeScript SDK

```bash
npm install solvens
```

### Quick Start

```typescript
import { Cosmos, Provider, createAgent } from 'solvens';

const cosmos = new Cosmos('my_workflow');

const claude = Provider.anthropic('claude-3-5-sonnet');
const architect = createAgent('architect', claude);

cosmos.task(architect, { name: 'design_api' });

const result = await cosmos.run({ simulate: true });
console.log(`Cost: $${result.estimatedCostUsd}`);
```

## Cosmos Language

`.cosmos` files define workflows in a simple DSL:

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

## Documentation

Full docs at [docs.solvens.amoris](https://docs.solvens.amoris)

## Author

Luis Alberto Burciaga Miker  
https://github.com/SolvensAmoris/solvens-core
