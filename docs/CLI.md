# SOLVENS CLI Reference

**Version:** 1.0.0

The SOLVENS CLI provides a command-line interface for managing workflows.

## Installation

```bash
pip install -e .
```

## Commands

### solvens version

Show version information.

```bash
solvens version
```

### solvens init

Initialize a new SOLVENS project.

```bash
solvens init --name my-workflow
solvens init --name my-workflow --path ./projects
```

### solvens compile

Compile a Cosmos workflow file.

```bash
solvens compile workflow.cosmos
solvens compile workflow.cosmos --strict
solvens compile workflow.cosmos --json
```

Options:
- `--strict`: Enable strict validation
- `--json`: Output JSON format

### solvens validate

Validate a Cosmos workflow file.

```bash
solvens validate workflow.cosmos
```

### solvens simulate

Simulate workflow execution without running providers.

```bash
solvens simulate workflow.cosmos
solvens simulate workflow.cosmos --json
```

This command calculates:
- Estimated cost
- Estimated time
- Memory usage
- Parallelism opportunities

### solvens run

Run a Cosmos workflow.

```bash
solvens run workflow.cosmos
solvens run workflow.cosmos --dry-run
```

### solvens explain

Explain a workflow DAG.

```bash
solvens explain workflow.cosmos
```

### solvens doctor

Check system configuration and dependencies.

```bash
solvens doctor
```

### solvens benchmark

Run performance benchmarks.

```bash
solvens benchmark
solvens benchmark --file workflow.cosmos
```

## Configuration

Configuration is stored in `.env` files:

```bash
# Providers
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here

# Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434

# Cost Limits
MAX_COST_PER_RUN=1.00
MAX_DAILY_COST=100.00
```

## Exit Codes

- `0`: Success
- `1`: Error

## Examples

### Complete Workflow

```bash
# Initialize project
solvens init --name demo

# Compile
solvens compile demo/demo.cosmos

# Validate
solvens validate demo/demo.cosmos

# Simulate (no cost)
solvens simulate demo/demo.cosmos

# Run (requires API keys)
solvens run demo/demo.cosmos
```

### Docker Usage

```bash
# Build and run
docker build -t solvens .
docker run solvens doctor

# With docker-compose
docker-compose up solvens
```
