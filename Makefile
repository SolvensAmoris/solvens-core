.PHONY: install test lint format clean build run help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -e ".[all,dev]"

install-dev: ## Install dev dependencies only
	pip install -e ".[dev]"

test: ## Run tests
	python -m pytest tests/ -v

test-cov: ## Run tests with coverage
	python -m pytest tests/ --cov=solvens --cov-report=html --cov-report=term

lint: ## Run linting
	python -m ruff check solvens/

format: ## Format code
	python -m ruff format solvens/

typecheck: ## Run type checking
	python -m mypy solvens/

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .ruff_cache/ .mypy_cache/
	rm -rf htmlcov/

build: clean ## Build package
	python -m build

run: ## Run the demo
	python -c "from solvens import __version__; print(f'SOLVENS CORE v{__version__}')"

demo: ## Run the demo script
	python -c "import asyncio; from solvens.agents import AgentOrchestrator; \
from solvens.router import CapabilityRouter; \
from solvens.core.types import TaskPriority; \
async def demo(): \
    router = CapabilityRouter(); await router.initialize(); \
    print(f'Router initialized with {len(router._rules)} rules'); \
    await router.shutdown(); \
asyncio.run(demo())"

publish: build ## Publish to PyPI
	twine upload dist/*

git-init: ## Initialize git repo and commit
	git init
	git add -A
	git commit -m "feat: Initial commit - SOLVENS CORE v0.1.0"

check: lint typecheck test ## Run all checks

.DEFAULT_GOAL := help
