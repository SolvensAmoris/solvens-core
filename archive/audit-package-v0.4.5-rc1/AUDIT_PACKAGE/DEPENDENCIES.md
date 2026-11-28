# SOLVENS CORE - Dependencies Document

**Version:** 0.4.5  
**Last Updated:** 2026-07-17

---

## 1. Programming Languages

| Language | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Primary language |

---

## 2. Python Dependencies

### 2.1 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | Latest | REST API framework |
| uvicorn | Latest | ASGI server |
| pydantic | Latest | Data validation |
| typer | Latest | CLI framework |
| rich | Latest | Terminal formatting |

### 2.2 AI/ML Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| openai | Latest | OpenAI API client |
| anthropic | Latest | Anthropic API client |
| aiohttp | Latest | Async HTTP client |
| httpx | Latest | HTTP client |

### 2.3 Parser Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| lark | Latest | PEG/LALR parser |

### 2.4 Visualization Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| networkx | Latest | Graph operations |
| matplotlib | Latest | Visualization |
| plotly | Latest | Interactive plots |

### 2.5 Dashboard Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | Latest | Web dashboard |

### 2.6 Testing Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | Latest | Testing framework |
| pytest-asyncio | Latest | Async test support |
| pytest-cov | Latest | Coverage reporting |

### 2.7 Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| python-dotenv | Latest | Environment variables |
| loguru | Latest | Logging |

---

## 3. pyproject.toml Dependencies

```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
    "openai>=1.0.0",
    "anthropic>=0.8.0",
    "aiohttp>=3.8.0",
    "httpx>=0.24.0",
    "lark>=1.1.0",
    "networkx>=3.0",
    "matplotlib>=3.7.0",
    "plotly>=5.18.0",
    "streamlit>=1.28.0",
    "python-dotenv>=1.0.0",
    "loguru>=0.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]
```

---

## 4. External Services

### 4.1 Cloud Providers (Optional)

| Service | Purpose | Required |
|---------|---------|----------|
| OpenAI API | GPT models | No (plugin) |
| Anthropic API | Claude models | No (plugin) |
| Google AI | Gemini models | No (plugin) |
| Grok API | Grok models | No (plugin) |
| DeepSeek API | DeepSeek models | No (plugin) |

### 4.2 Local Providers

| Service | Purpose | Required |
|---------|---------|----------|
| Ollama | Local models | No (plugin) |

### 4.3 Infrastructure

| Service | Purpose | Required |
|---------|---------|----------|
| PostgreSQL | Persistent storage | No (optional) |
| Redis | Cache layer | No (optional) |
| SQLite | Local storage | No (default) |

---

## 5. Development Tools

| Tool | Purpose |
|------|---------|
| ruff | Linting |
| mypy | Type checking |
| black | Code formatting |
| isort | Import sorting |
| pre-commit | Git hooks |

---

## 6. Containerization

### 6.1 Docker

| Base Image | Purpose |
|------------|---------|
| python:3.11-slim | Production runtime |
| python:3.11-bookworm | Development |

### 6.2 Docker Compose Services

| Service | Image | Purpose |
|---------|-------|---------|
| solvens-core | Build | Main application |
| ollama | ollama/ollama | Local models |
| postgres | postgres:15 | Database |
| redis | redis:7 | Cache |

---

## 7. System Dependencies

| Package | Purpose |
|---------|---------|
| git | Version control |
| docker | Containerization |
| systemd | Service management (Linux) |

---

## 8. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | No | OpenAI API key |
| ANTHROPIC_API_KEY | No | Anthropic API key |
| GOOGLE_API_KEY | No | Google AI API key |
| SOLVENS_ENV | No | Environment (dev/prod) |
| SOLVENS_DB_URL | No | Database connection |

---

**End of Dependencies Document**
