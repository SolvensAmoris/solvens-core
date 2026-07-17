# Contributing to SOLVENS CORE

Thank you for your interest in contributing to SOLVENS CORE!

## Project Overview

SOLVENS CORE is an AI Operating System designed to be modular, extensible, and provider-agnostic. We welcome contributions from developers of all skill levels.

## How to Contribute

### Reporting Bugs

1. Check if the bug is already reported in [Issues](../../issues)
2. Create a detailed bug report including:
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages

### Suggesting Features

1. Check existing [Issues](../../issues) for similar suggestions
2. Create a feature request with:
   - Clear description
   - Use case
   - Potential implementation approach

### Pull Requests

#### Before Submitting

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Make your changes following our coding standards

#### Coding Standards

- **Style**: Follow PEP 8, use Black for formatting
- **Types**: Add type hints to all functions
- **Docs**: Document public APIs with docstrings
- **Tests**: Add tests for new functionality

#### Commit Messages

Use conventional commits:

```
feat: add new provider adapter
fix: resolve routing bug
docs: update README
test: add integration tests
refactor: improve performance
```

#### PR Description

Include:
- Summary of changes
- Related issue numbers
- Testing performed
- Screenshots (if applicable)

## Development Setup

### Prerequisites

- Python 3.11+
- git
- pip or uv

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/solvens-core.git
cd solvens-core

# Add upstream
git remote add upstream https://github.com/SolvensAmoris/solvens-core.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=solvens --cov-report=html

# Specific test file
pytest tests/unit/test_router.py -v
```

### Code Quality

```bash
# Format code
ruff format solvens/

# Lint
ruff check solvens/

# Type check
mypy solvens/
```

## Project Structure

```
solvens-core/
├── solvens/              # Main package
│   ├── core/            # Core abstractions
│   ├── agents/          # Agent system
│   ├── router/          # Capability routing
│   ├── providers/       # Provider interfaces
│   ├── plugins/         # Provider plugins
│   ├── registry/        # Plugin system
│   ├── api/             # REST API
│   └── cli/             # CLI interface
├── docs/                 # Documentation
├── tests/               # Test suite
└── docker/              # Docker configuration
```

## Adding a New Provider

1. Create plugin directory: `solvens/plugins/myprovider/`
2. Implement `ProviderClient` interface
3. Add tests
4. Update documentation

Example:

```python
# solvens/plugins/myprovider/__init__.py
from solvens.providers.base import ProviderClient
from solvens.core.types import ProviderType, Response

class MyProviderClient(ProviderClient):
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.MY_PROVIDER
    
    async def chat(self, messages, **options) -> Response:
        # Implementation
        ...
```

## Adding a New Routing Rule

Edit `solvens/router/rules.py`:

```python
RoutingRule(
    name="my_rule",
    patterns=[r"\bkeyword\s+"],
    provider=ProviderType.MY_PROVIDER,
    priority=75,
)
```

## Documentation

Update documentation for any changes:

- `README.md` - Overview and setup
- `docs/` - Detailed documentation
- Docstrings - API documentation

## Code Review Process

1. Automated checks must pass (lint, tests, type check)
2. At least one maintainer approval required
3. Address review feedback
4. Squash commits before merging

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open an [Issue](../../issues/new)
- Email: support@solvens.amoris
- Discord: (link coming soon)

## Recognition

Contributors will be recognized in:
- Release notes
- README contributors section
- Project documentation

Thank you for making SOLVENS CORE better! 🚀
