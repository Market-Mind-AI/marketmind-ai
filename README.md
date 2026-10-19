# MarketMind AI — Frontend

> **Framework de Inteligencia Comercial basado en IA Generativa** para identificar oportunidades de mercado a partir de datos públicos globales.

This repository is the **Astro frontend** for MarketMind. It turns a single
product (a photo + a free-text description) into an **explainable market-opportunity
report**: a Market Opportunity Score (MOS) per country, the resulting ranking, and
a business narrative — every number computed by the backend, never by the browser.

The backend the browser talks to is the **marketmind-orchestrator** (FastAPI +
LangGraph agent, host port `8081` in dev). It is the entry point since 21/09/2026
and calls **marketmind-scoring** (formerly `marketmind-core`, host port `8004`),
the method engine. The scoring service exposes the same `/analyze`, `/catalog` and
`/countries` routes, so pointing the app at `8004` also works — but it bypasses
the agent.

Final project (TFM) for the *Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa* — **EBIS Business Techschool**.

## Team
- **Miguel Antonio Blanco Salcedo** — [@mikews93](https://github.com/mikews93)
- **Álvaro Augusto De Marco Neto** — [@ironeto](https://github.com/ironeto)

## Flow

1. **Upload** a product photo + a short description and pick the **target markets**
   (ISO3 countries, from `GET /countries`).
2. **Identify** — `POST /catalog/identify-image` runs a vision LLM and returns the
   identified product plus, per country, the curated search vocabulary and the
   ranked *reference-market candidates*.
3. **Review & edit** — the user confirms/corrects every field (name, brand,
   category, price, per-country search terms, reference candidates) before any
   paid data collection runs. This is the human-curation gate the method is designed around.
4. **Analyze** — `POST /analyze` (202 Accepted) kicks off the background pipeline:
   ensure data freshness → Cap. 4 indicators → Cap. 5 MOS (per country). The
   request lands in the pending-analyses dock; the user can queue more.
5. **Report** — the app subscribes to `GET /analyze/{request_id}/stream` (SSE) for
   live status/progress, and polls `GET /analyze/{request_id}` only as a fallback
   (every 2.5 s without a stream, every 15 s while the stream is alive; gives up
   after 6 min). It renders the MOS ranking, each country's interpretation band,
   the grouped per-dimension scores and the LLM business narrative. Every report
   has a share link at `/r/{slug}`.

## Setup

```bash
cd web
npm install
cp .env.example .env    # PUBLIC_API_BASE=http://localhost:8081
npm run dev             # http://localhost:4321
```

The orchestrator must be running on `PUBLIC_API_BASE` (default
`http://localhost:8081`) with CORS allowing the dev origin (`http://localhost:4321`).
Set `PUBLIC_API_BASE=http://localhost:8004` to talk to the scoring service directly
(same routes, no agent).

Convenience targets from the repo root: `make install`, `make dev`, `make build`, `make preview`
(`make help` lists them).

## Backend contract (`web/src/lib/api.ts`)

- `GET /countries` — available markets `{ iso3, name, iso2, continent }[]`, ordered by continent then name
- `POST /catalog/identify-image` — `{ image_base64, image_media_type, hint_text, countries }`
- `POST /analyze` — the confirmed identify-image fields + `countries` → `{ request_id, status }`
- `GET /analyze/{request_id}/stream` — SSE: `{ status, progress, has_explanation, narrative_abandoned }` on every change
- `GET /analyze/{request_id}` — `{ status, progress, result: MosResult[], explanation, breakdown, ... }`

## Production

`PUBLIC_API_BASE=/api` is baked into the bundle at build time (`Dockerfile` ARG;
Astro inlines `PUBLIC_*` at build, so a container env var would do nothing). The
ingress on BeProfit's AKS routes `/api` → orchestrator and `/scoring` → scoring,
so every call is same-origin. The image is the static `dist/` served by
`nginx-unprivileged` on container port `8080` (`nginx/default.conf` rewrites
`/report/*` and `/r/*` to the placeholder documents client-side routing needs).

Build and deploy: `.github/workflows/build-and-push.yml` builds on push to `main`,
pushes `ghcr.io/market-mind-ai/marketmind-ai`, then bumps the image tag in
`equifina/beprofit-infra-manifests` (`env/marketmind-dev/web-values.yaml`), which
ArgoCD rolls out.

## Prototypes

Clickable HTML prototypes from June 2026, kept as design references under
[`docs/historico/`](docs/historico/). They predate the build: Streamlit, pgvector,
Google Trends and GKE no longer apply.

- **[`docs/historico/marketmind-app.html`](docs/historico/marketmind-app.html)** — the original product UI concept.
- **[`docs/historico/marketmind-plan.html`](docs/historico/marketmind-plan.html)** — the architecture & plan one-pager.

## Tech

| Layer | Choice |
|---|---|
| Frontend | **Astro 5 + View Transitions API**, static output (`web/`) |
| State/flow | client-side (dynamic `/report/[id]` and `/r/[slug]` resolved in the browser; pending requests in `localStorage`) |
| Backend | **marketmind-orchestrator** (separate repo, FastAPI + LangGraph) — the agent is the entry point since 21/09/2026; it calls **marketmind-scoring** (formerly `marketmind-core`), the method engine. In dev, `/api` on the ingress goes to the orchestrator and `/scoring` to the scoring. |
| Serving | `nginx-unprivileged` (port 8080) on BeProfit's AKS, GitOps via ArgoCD |
