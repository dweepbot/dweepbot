.PHONY: help install install-dev test lint format clean docs run

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "DweepBot Pro - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package with core dependencies
	pip install -e .

install-dev: ## Install package with development dependencies
	pip install -e ".[dev]"

install-all: ## Install package with all optional dependencies
	pip install -e ".[all]"

test: ## Run tests with coverage
	pytest --cov=dweepbot --cov-report=html --cov-report=term-missing

test-quick: ## Run tests without coverage
	pytest -v

lint: ## Run linters (flake8, mypy)
	flake8 dweepbot tests
	mypy dweepbot

format: ## Format code with black and isort
	black dweepbot tests examples
	isort dweepbot tests examples

format-check: ## Check code formatting without making changes
	black --check dweepbot tests examples
	isort --check-only dweepbot tests examples

clean: ## Clean up build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs: ## Build documentation
	@echo "Documentation building not yet configured"

run: ## Run the CLI
	python -m cli

run-example: ## Run example workflow
	python examples/simple_task.py

pre-commit: format lint test ## Run all checks before committing

build: clean ## Build distribution packages
	python -m build

publish-test: build ## Publish to TestPyPI
	python -m twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI
	python -m twine upload dist/*

docker-build: ## Build Docker image
	docker build -t dweepbot:latest .

docker-run: ## Run Docker container
	docker run -it --rm --env-file .env dweepbot:latest

setup: ## Initial setup (copy .env.example and install dev dependencies)
	cp .env.example .env
	$(MAKE) install-dev
	@echo ""
	@echo "✅ Setup complete! Edit .env with your API keys."

version: ## Show version
	@python -c "from dweepbot import __version__; print(__version__)"
