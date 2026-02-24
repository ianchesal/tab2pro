.PHONY: lint format security test test-all check install

install:
	uv sync

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

security:
	uv run bandit -r src/tab2pro -c pyproject.toml
	uv run pip-audit

test:
	uv run pytest -m "not integration" --cov=tab2pro --cov-report=term-missing

test-all:
	uv run pytest --cov=tab2pro --cov-report=term-missing

# Run all checks that CI runs (lint + security + unit tests)
check: lint security test
