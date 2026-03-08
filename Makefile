.PHONY: venv setup test lint clean

PYTHON := python3
UV := uv

venv:
	$(UV) venv

setup: venv
	$(UV) sync

test:
	$(UV) run pytest tests/ -v

lint:
	$(UV) run ruff check bed/
	$(UV) run ruff format --check bed/

clean:
	rm -rf .venv __pycache__ dist build .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
