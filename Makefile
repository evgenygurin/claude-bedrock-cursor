.PHONY: help install dev test lint format quality security clean setup-aws setup-cursor deploy docs

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	uv sync --no-dev

dev:  ## Install development dependencies
	uv sync --all-extras

test:  ## Run all tests with coverage
	uv run pytest

test-unit:  ## Run only unit tests
	uv run pytest tests/unit/ -v

test-integration:  ## Run only integration tests
	uv run pytest tests/integration/ -v

test-e2e:  ## Run only e2e tests
	uv run pytest tests/e2e/ -v

lint:  ## Run linters (ruff + mypy)
	uv run ruff check src/ tests/
	uv run mypy src/ tests/

format:  ## Format code with ruff
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

quality:  ## Run all quality checks
	@echo "🔍 Running quality checks..."
	@make format
	@make lint
	@make test
	@echo "✅ All quality checks passed!"

security:  ## Run comprehensive security scans
	@./scripts/security_scan.sh

pre-commit-install:  ## Install pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

pre-commit-run:  ## Run pre-commit hooks manually
	uv run pre-commit run --all-files

clean:  ## Clean build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

setup-aws:  ## Setup AWS Bedrock configuration
	@./scripts/setup_aws.sh

setup-cursor:  ## Setup Cursor IDE integration
	@./scripts/setup_cursor.sh

configure:  ## Run interactive configuration
	uv run claude-bedrock configure

init:  ## Initialize project
	uv run claude-bedrock init

status:  ## Show current status
	uv run claude-bedrock status

health:  ## Run health check
	./scripts/health_check.sh

deploy:  ## Deploy configuration to AWS Bedrock
	./scripts/configure_bedrock.sh

docs:  ## Generate documentation
	@echo "📚 Documentation available in docs/"
	@echo "See README.md for quick start"

build:  ## Build distribution packages
	uv build

publish:  ## Publish to PyPI
	uv publish

pre-commit:  ## Install pre-commit hooks
	uv run pre-commit install

check-deps:  ## Check for outdated dependencies
	uv pip list --outdated

update-deps:  ## Update dependencies
	uv sync --upgrade

lock:  ## Lock dependencies
	uv lock

all:  ## Run full workflow (format, lint, test, security)
	@make format
	@make quality
	@make security
	@echo "🎉 All checks passed! Ready to commit."
