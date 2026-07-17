# Cosmos Hub

Marketplace for SOLVENS workflows and agents.

## Concept

Cosmos Hub is to AI agents what npm is to JavaScript packages - a centralized marketplace for discovering, sharing, and monetizing AI agent workflows.

## Features

- 🔍 **Explore** - Search workflows by category, provider, cost
- 🤖 **Agents** - Pre-built agents: architect, tester, doc-writer
- 📦 **Publish** - Share your workflows with the community
- 💰 **Monetize** - Set prices and earn from your workflows
- 🍴 **Fork** - Base workflows on others' work

## Architecture

```
hub/
├── app/              # Next.js app
│   ├── api/         # API routes
│   └── workflows/   # Page templates
├── prisma/          # Database schema
└── lib/             # Utilities
```

## Tech Stack

- Next.js 14 (App Router)
- Prisma + PostgreSQL
- NextAuth.js
- Vercel

## Getting Started

```bash
cd hub
npm install
npx prisma generate
npm run dev
```

## Workflow Format

Workflows are published as `.cosmos` files with metadata:

```json
{
  "name": "@username/workflow-name",
  "version": "1.0.0",
  "price": 5.00,
  "description": "Generate a complete CRM system",
  "author": "luis",
  "tags": ["crm", "fullstack", "api"]
}
```

## API

| Endpoint | Description |
|----------|-------------|
| GET /api/workflows | List workflows |
| GET /api/workflows/:id | Get workflow |
| POST /api/workflows | Publish workflow |
| GET /api/workflows/:id/rate | Rate workflow |

## Revenue Model

- 80/20 revenue split (creator/platform)
- Free workflows supported
- Subscription tiers for enterprise

## Author

Luis Alberto Burciaga Miker  
https://github.com/SolvensAmoris/solvens-core
