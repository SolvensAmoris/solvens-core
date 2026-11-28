# SOLVENS CORE - Configuration Document

**Version:** 0.4.5  
**Last Updated:** 2026-07-17

---

## 1. Environment Variables

### 1.1 API Keys (Optional - Plugins)

**NOTE: These are NOT included in the audit package. Configure in your own environment.**

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | No | OpenAI API key for GPT models |
| ANTHROPIC_API_KEY | No | Anthropic API key for Claude models |
| GOOGLE_API_KEY | No | Google AI API key for Gemini models |
| GROK_API_KEY | No | Grok API key |
| DEEPSEEK_API_KEY | No | DeepSeek API key |
| OLLAMA_BASE_URL | No | Ollama server URL (default: http://localhost:11434) |

### 1.2 Application Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| SOLVENS_ENV | development | Environment (development/staging/production) |
| SOLVENS_HOST | 0.0.0.0 | Host to bind to |
| SOLVENS_PORT | 8000 | Port to bind to |
| SOLVENS_LOG_LEVEL | INFO | Logging level |
| SOLVENS_DB_URL | sqlite:///solvens.db | Database connection string |
| SOLVENS_REDIS_URL | redis://localhost:6379 | Redis connection string |
| SOLVENS_SECRET_KEY | - | Secret key for encryption |

### 1.3 Provider Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| SOLVENS_DEFAULT_PROVIDER | openai | Default AI provider |
| SOLVENS_PROVIDER_TIMEOUT | 60 | Provider request timeout (seconds) |
| SOLVENS_MAX_RETRIES | 3 | Maximum retry attempts |

### 1.4 Cosmos Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| COSMOS_MAX_TOKENS | 2048 | Maximum tokens per request |
| COSMOS_TEMPERATURE | 0.7 | Default temperature |
| COSMOS_STRICT_MODE | true | Strict validation mode |

---

## 2. Configuration Files

### 2.1 pyproject.toml

Main project configuration file.

```toml
[project]
name = "solvens-core"
version = "0.4.5"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

### 2.2 .env.example

Template for environment variables:

```env
# API Keys (DO NOT COMMIT)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Application
SOLVENS_ENV=development
SOLVENS_LOG_LEVEL=INFO

# Server
SOLVENS_HOST=0.0.0.0
SOLVENS_PORT=8000

# Database
SOLVENS_DB_URL=sqlite:///solvens.db

# Providers
SOLVENS_DEFAULT_PROVIDER=openai
```

### 2.3 solvens/config/settings.py

Main configuration module.

---

## 3. Execution Commands

### 3.1 Installation

```bash
# Install dependencies
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### 3.2 Running the Application

```bash
# Direct Python
python -m solvens

# With uvicorn
uvicorn solvens.api.main:app --reload

# With Docker
docker build -t solvens-core .
docker run -p 8000:8000 solvens-core
```

### 3.3 CLI Commands

```bash
# Start chat
solvens chat "Your prompt"

# Run diagnostics
solvens doctor

# List providers
solvens providers list

# Manage plugins
solvens plugins list
solvens plugins install <plugin-name>

# List available models
solvens models list

# Schedule tasks
solvens schedule run <workflow-file>
```

### 3.4 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest cosmos/tests/test_llama_full.py

# Run with coverage
pytest --cov=solvens --cov-report=html

# Run compiler
python -m cosmos.compiler temporal_violation.cosmos --strict
```

### 3.5 Linting & Type Checking

```bash
# Lint
ruff check solvens/

# Format
ruff format solvens/

# Type check
mypy solvens/
```

---

## 4. Docker Configuration

### 4.1 Dockerfile

Multi-stage build for production.

### 4.2 docker-compose.yml

```yaml
services:
  solvens:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SOLVENS_ENV=production
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
```

### 4.3 Building & Running

```bash
# Build image
docker build -t solvens-core .

# Run container
docker run -d --name solvens \
  -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  solvens-core

# With docker-compose
docker-compose up -d
```

---

## 5. Systemd Service

### 5.1 solvens.service

```ini
[Unit]
Description=Solvens Core AI Operating System
After=network.target

[Service]
Type=simple
User=solvens
WorkingDirectory=/opt/solvens
ExecStart=/usr/bin/python -m solvens
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5.2 Installation

```bash
sudo cp solvens.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable solvens
sudo systemctl start solvens
```

---

## 6. Dashboard Configuration

### 6.1 Running Dashboard

```bash
streamlit run solvens/dashboard/app.py
```

### 6.2 Dashboard Features

- Agent monitoring
- Task queue visualization
- Provider status
- Cost tracking
- Usage analytics
- Memory usage
- Logs and errors

---

## 7. Cosmos Compiler Configuration

### 7.1 Compiler Usage

```bash
# Compile .cosmos file
python -m cosmos.compiler <file.cosmos>

# With strict mode (fail on first error)
python -m cosmos.compiler <file.cosmos> --strict

# Dump AST
python -m cosmos.compiler <file.cosmos> --dump-ast
```

### 7.2 Example .cosmos File

```cosmos
universe "example" {
    metadata {
        version: "0.4.5"
        author: "Author Name"
        standard: "Cosmos IR v0.4.5"
    }
    sun Sol
    light {
        from: Sol
        to: Target
        flow: Primary
        restringido_hasta: 2027-01-01
    }
}
```

---

## 8. Security Notes

### 8.1 Secrets Management

- **NEVER** commit API keys to version control
- Use `.env` files for local development
- Use Docker Secrets for production
- Use environment variables injected at runtime

### 8.2 .gitignore

The following should be ignored:
- `.env` (contains secrets)
- `*.db` (database files)
- `__pycache__/` (Python cache)
- `.pytest_cache/` (test cache)
- `*.egg-info/` (package info)
- `node_modules/` (if any)

---

**End of Configuration Document**
