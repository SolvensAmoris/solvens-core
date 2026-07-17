# SOLVENS CORE Dashboard

Real-time DAG visualization and execution dashboard for SOLVENS CORE.

## Features

- 🌌 **Live DAG Visualization** - React Flow powered graph view
- 🔮 **Pre-execution Simulator** - Estimate cost and time before running
- 📊 **Real-time Metrics** - Track cost, tokens, parallelism
- 📜 **Live Logs** - Streaming execution logs
- 🤖 **Multi-provider Support** - OpenAI, Anthropic, Google, Ollama, DeepSeek

## Quick Start

### Backend

```bash
cd dashboard/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd dashboard/web
npm install
npm run dev
```

Open http://localhost:3000

## Environment Variables

### Backend (.env)
```
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Architecture

```
dashboard/
├── api/              # FastAPI backend
│   └── main.py       # WebSocket + REST endpoints
└── web/              # Next.js frontend
    ├── app/          # App router pages
    ├── components/    # React components
    └── lib/          # State management
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/runs` | List all runs |
| GET | `/api/run/{id}` | Get run details |
| POST | `/api/simulate` | Simulate workflow |
| POST | `/api/run` | Start new run |
| WS | `/ws/run/{id}` | WebSocket for live updates |

## WebSocket Messages

```typescript
// Task started
{ type: "task_start", data: { task: "design_api", provider: "claude" } }

// Task completed
{ type: "task_end", data: { task: "design_api", tokens: 1200, cost: 0.018 } }

// Metrics update
{ type: "metric_update", data: { parallelism: 4, reuse: 0.47 } }

// Run completed
{ type: "run_end", data: { status: "completed", total_cost: 0.18 } }
```

## Author

Luis Alberto Burciaga Miker  
https://github.com/SolvensAmoris/solvens-core
