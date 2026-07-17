# SOLVENS CORE Deployment Guide

**Version:** 0.1.0

---

## Prerequisites

- Python 3.11+
- pip or uv
- Docker (optional)
- API keys for desired providers

## Installation

### Option 1: pip

```bash
pip install -e ".[all]"
```

### Option 2: uv (Recommended)

```bash
uv sync --all-extras
```

### Option 3: Docker

```bash
docker-compose -f docker/docker-compose.yml up -d
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | For GPT models |
| `ANTHROPIC_API_KEY` | Anthropic API key | For Claude models |
| `GOOGLE_API_KEY` | Google API key | For Gemini models |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | SOLVENS CORE | Application name |
| `DEBUG` | false | Enable debug mode |
| `LOG_LEVEL` | INFO | Logging level |
| `API_HOST` | 0.0.0.0 | API host |
| `API_PORT` | 8000 | API port |
| `DEFAULT_PROVIDER` | openai | Default AI provider |
| `FALLBACK_PROVIDER` | ollama | Fallback provider |

## Running

### API Server

```bash
uvicorn solvens.api.main:app --host 0.0.0.0 --port 8000
```

Or with auto-reload:

```bash
uvicorn solvens.api.main:app --reload
```

### CLI

```bash
solvens --help
```

Available commands:
- `solvens doctor` - Check system health
- `solvens providers` - List providers
- `solvens models` - List models
- `solvens plugins` - List plugins
- `solvens info` - System information

## Docker Deployment

### Build Image

```bash
docker build -f docker/Dockerfile -t solvens-core .
```

### Run Container

```bash
docker run -d \
  --name solvens \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e ANTHROPIC_API_KEY=your_key \
  solvens-core
```

### Docker Compose

```bash
# Basic
docker-compose -f docker/docker-compose.yml up -d

# With Ollama (local inference)
docker-compose -f docker/docker-compose.yml --profile with-ollama up -d
```

### Docker Secrets

Create secrets in `/run/secrets/`:

```yaml
# docker-compose.yml
secrets:
  openai_key:
    file: ./secrets/openai_key.txt
  anthropic_key:
    file: ./secrets/anthropic_key.txt

services:
  solvens:
    secrets:
      - openai_key
      - anthropic_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_key
```

## Systemd Service

### Install

```bash
cp docker/solvens.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable solvens
systemctl --user start solvens
```

### Check Status

```bash
systemctl --user status solvens
journalctl --user -u solvens -f
```

## Kubernetes Deployment

### Helm Chart (Coming Soon)

```bash
helm repo add solvens https://charts.solvens.amoris
helm install solvens-core solvens/solvens-core
```

### Manual YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: solvens-core
spec:
  replicas: 2
  selector:
    matchLabels:
      app: solvens-core
  template:
    metadata:
      labels:
        app: solvens-core
    spec:
      containers:
      - name: solvens
        image: solvens/solvens-core:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
```

## Health Checks

### API Health

```bash
curl http://localhost:8000/health
```

### Provider Health

```bash
curl http://localhost:8000/providers/openai/health
```

## Monitoring

### Metrics Endpoint

```bash
curl http://localhost:8000/status
```

### Logs

```bash
# View logs
docker logs solvens -f

# Or in development
uvicorn solvens.api.main:app --log-level debug
```

## Troubleshooting

### Provider Not Responding

1. Check API key is set correctly
2. Verify network connectivity
3. Check provider status pages:
   - OpenAI: status.openai.com
   - Anthropic: status.anthropic.com

### Memory Issues

Increase container memory or switch to Redis backend:

```bash
MEMORY_BACKEND=redis REDIS_URL=redis://redis:6379 uvicorn solvens.api.main:app
```

### Performance Issues

1. Enable connection pooling
2. Use local providers (Ollama) when possible
3. Adjust worker count:
   ```bash
   uvicorn solvens.api.main:app --workers 4
   ```

## Security

### Production Checklist

- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS/TLS
- [ ] Set up rate limiting
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Regular security updates

### Docker Security

```bash
# Run as non-root
docker run -u 1000 solvens-core

# Read-only filesystem
docker run --read-only solvens-core

# No new privileges
docker run --security-opt=no-new-privileges solvens-core
```

## Backup

### Data Directory

```bash
tar -czf solvens-backup.tar.gz ~/.solvens/
```

### Restore

```bash
tar -xzf solvens-backup.tar.gz -C ~/
```

## Updates

### pip

```bash
pip install --upgrade solvens-core
```

### Docker

```bash
docker-compose pull
docker-compose up -d
```

## Support

- Documentation: docs.solvens.amoris
- Issues: github.com/SolvensAmoris/solvens-core/issues
- Email: support@solvens.amoris
