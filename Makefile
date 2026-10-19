# MarketMind AI — frontend-only convenience targets.
# The backend is the separate marketmind-orchestrator (host port 8081 in dev),
# which calls marketmind-scoring (8004); this repo is just the Astro frontend
# that talks to it over HTTP.
# Run `make help` for the list.

.DEFAULT_GOAL := help

.PHONY: help install dev build preview

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
