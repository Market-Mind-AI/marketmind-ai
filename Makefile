# MarketMind AI — convenience targets. These delegate to docker compose / uv.
# Run `make help` for the list.

COMPOSE ?= docker compose

.DEFAULT_GOAL := help

.PHONY: help up down logs ps build api-test fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Start the full stack (db + api + web) in the background
	$(COMPOSE) up -d --build

down: ## Stop the stack and remove containers
	$(COMPOSE) down

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## Show running services
	$(COMPOSE) ps

build: ## Build all service images
	$(COMPOSE) build

api-test: ## Run the api test suite (uv, run from ./api)
	cd api && uv run pytest

fmt: ## Format infra HCL
	terraform -chdir=infra/terraform fmt -recursive
