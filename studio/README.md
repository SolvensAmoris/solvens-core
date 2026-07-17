# SOLVENS Studio

AI-Native IDE for building, simulating, and deploying AI agent workflows.

## Features

- 🌌 **Monaco Editor** - Full IDE with Cosmos Language support
- 📊 **Live DAG Preview** - See your workflow as a graph while you type
- 🤖 **AI Copilot** - Generate code with natural language
- 🔮 **Real-time Simulation** - See cost/time estimates as you edit
- 👥 **Collaborative** - Yjs for real-time collaboration (coming soon)
- 🚀 **One-click Deploy** - Deploy to cloud with a single button

## Quick Start

```bash
cd studio
npm install
npm run dev
```

Open http://localhost:3000

## Architecture

```
studio/
├── app/
│   ├── page.tsx           # Main IDE layout
│   ├── layout.tsx         # Root layout
│   └── api/
│       └── ai/
│           └── complete/  # Copilot API
├── components/
│   ├── MonacoEditor.tsx   # Code editor
│   ├── DAGPreview.tsx     # React Flow DAG
│   ├── Copilot.tsx        # AI suggestions
│   └── SimulationPanel.tsx
└── lib/
    └── store.ts           # Zustand state
```

## Cosmos Language

Write workflows in the Cosmos DSL:

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

## Meta Builder

Build workflows from prompts:

```bash
python -m meta.cli "build me a CRM for dentists with billing"
```

## Demo Mode

Visit `/demo` for a pre-loaded demo workflow.

## Author

Luis Alberto Burciaga Miker  
https://github.com/SolvensAmoris/solvens-core
