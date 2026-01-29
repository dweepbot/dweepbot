.PHONY: help install install-dev install-all test lint format clean docs

help:
	@echo "DweepBot Development Commands"
	@echo "=============================="
	@echo "install       - Install core dependencies"
	@echo "install-dev   - Install development dependencies"
	@echo "install-all   - Install all dependencies (core + all extras)"
	@echo "test          - Run tests"
	@echo "test-cov      - Run tests with coverage"
	@echo "lint          - Run linters"
	@echo "format        - Format code"
	@echo "clean         - Clean build artifacts"
	@echo "docs          - Build documentation (future)"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all,dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=dweepbot --cov-report=html --cov-report=term

test-integration:
	pytest tests/integration/ -v

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/ examples/
	ruff check --fix src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	@echo "Documentation generation coming soon..."
