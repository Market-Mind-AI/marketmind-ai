# MarketMind AI — frontend targets, plus the one-machine deploy of the whole
# system (deploy/docker-compose.yml: database, collectors, scoring,
# orchestrator and this frontend). Run `make help` for the list.
#
# Frontend in dev talks to the separate marketmind-orchestrator (host port 8081),
# which calls marketmind-scoring (8004).

.DEFAULT_GOAL := help

COMPOSE := docker compose -f deploy/docker-compose.yml --env-file deploy/.env

.PHONY: help install dev build preview up down bootstrap logs ps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install web dependencies
	cd web && npm install

dev: ## Start the Astro dev server (http://localhost:4321)
	cd web && npm run dev

build: ## Build static output to web/dist/
	cd web && npm run build

preview: ## Preview the production build
	cd web && npm run preview

# ---- Whole system, one machine (see deploy/README.md) ----

deploy/.env:
	@echo "deploy/.env is missing: cp deploy/.env.example deploy/.env and fill in the REQUIRED values" >&2; exit 1

up: deploy/.env ## Build and start every service (add PROFILE=local-llm for the Ollama gateway)
	$(COMPOSE) $(if $(PROFILE),--profile $(PROFILE)) up -d --build

down: deploy/.env ## Stop the stack (data volume is kept; `make down V=1` removes it)
	$(COMPOSE) --profile local-llm down $(if $(V),-v)

bootstrap: deploy/.env ## Wait for the services, calibrate MOS weights, print the scoring health
	./deploy/bootstrap.sh

logs: deploy/.env ## Follow the logs (S=scoring for one service)
	$(COMPOSE) logs -f --tail=200 $(S)

ps: deploy/.env ## Status of the containers
	$(COMPOSE) ps
