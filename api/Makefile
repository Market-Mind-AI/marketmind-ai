# =============================================================================
# MarketMind AI — developer tasks
# =============================================================================
.DEFAULT_GOAL := help
.PHONY: help install run test lint typecheck arch fmt check

UV ?= uv

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Sync all deps (incl. dev group) into the uv-managed venv
	$(UV) sync

run: ## Run the FastAPI app (offline/all-fakes by default) with reload
	$(UV) run uvicorn marketmind.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run the test suite
	$(UV) run pytest

lint: ## Lint with ruff
	$(UV) run ruff check src tests

typecheck: ## Static type-check with mypy
	$(UV) run mypy src

arch: ## Enforce the dependency rule (import-linter)
	$(UV) run lint-imports

fmt: ## Auto-format + fix imports with ruff
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

check: lint typecheck arch test ## Run all quality gates
