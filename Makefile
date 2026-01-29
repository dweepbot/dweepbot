.PHONY: install test clean

install:
	pip install -e ".[full]"

test:
	python -m pytest tests/ -v

lint:
	ruff check src/
	black --check src/

format:
	black src/
	ruff --fix src/

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
