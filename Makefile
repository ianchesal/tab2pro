.PHONY: lint format security test test-all check install uninstall

INSTALL_DIR := $(HOME)/.local/bin
WRAPPER     := $(INSTALL_DIR)/tab2pro
PROJECT_DIR := $(CURDIR)

install:
	uv sync
	mkdir -p $(INSTALL_DIR)
	@printf '#!/usr/bin/env bash\n# Wrapper for tab2pro — runs from any directory; output goes to your CWD.\nexec uv run --project %s tab2pro "$$@"\n' "$(PROJECT_DIR)" > $(WRAPPER)
	chmod +x $(WRAPPER)
	@echo "Installed: $(WRAPPER)"

uninstall:
	rm -f $(WRAPPER)
	@echo "Removed: $(WRAPPER)"

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
