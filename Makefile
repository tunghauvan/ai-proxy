# Makefile for LangChain Proxy development

.PHONY: help install install-dev test test-unit test-integration lint format type-check clean build docs serve docker-build docker-up docker-down

# Default target
help: ## Show this help message
	@echo "LangChain Proxy Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install the package
	pip install -e .

install-dev: ## Install with development dependencies
	pip install -e ".[dev]"

# Testing
test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

test-e2e: ## Run end-to-end tests only
	pytest tests/e2e/

test-coverage: ## Run tests with coverage
	pytest --cov=langchain_proxy --cov-report=html --cov-report=term

# Code quality
lint: ## Run linting
	flake8 src/ tests/

format: ## Format code with Black and isort
	black src/ tests/
	isort src/ tests/

type-check: ## Run type checking with mypy
	mypy src/

quality: lint format type-check ## Run all code quality checks

# Cleanup
clean: ## Clean up build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build
build: ## Build the package
	python -m build

# Documentation
docs: ## Build documentation
	pip install -e ".[docs]"
	cd docs && make html

docs-serve: ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8001

# Development server
serve: ## Start the development server
	uvicorn langchain_proxy.server.main:app --reload --host 0.0.0.0 --port 8000

serve-prod: ## Start the production server
	uvicorn langchain_proxy.server.main:app --host 0.0.0.0 --port 8000 --workers 4

# Docker
docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all Docker services
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

# CLI shortcuts
cli: ## Run CLI commands (pass COMMAND as argument)
	langchain-proxy $(COMMAND)

# Database
db-init: ## Initialize database
	langchain-proxy-server --init-db

db-migrate: ## Run database migrations
	alembic upgrade head

# Deployment
deploy-dev: ## Deploy to development environment
	@echo "Deploying to development..."
	# Add your deployment commands here

deploy-prod: ## Deploy to production environment
	@echo "Deploying to production..."
	# Add your deployment commands here

# CI/CD
ci: clean install-dev quality test ## Run CI pipeline locally