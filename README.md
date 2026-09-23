# MarketMind AI — Frontend

> **Framework de Inteligencia Comercial basado en IA Generativa** para identificar oportunidades de mercado a partir de datos públicos globales.

This repository is the **Astro frontend** for MarketMind. It turns a single
product (a photo + a free-text description) into an **explainable market-opportunity
report**: a Market Opportunity Score (MOS) per country, the resulting ranking, and
a business narrative — every number computed by the backend, never by the browser.

The backend is the separate **marketmind-orchestrator** service (FastAPI, host port
`8004`); this app talks to it over HTTP. The former bundled `api/` prototype has
been removed — the frontend now integrates directly with the real Core.

Final project (TFM) for the *Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa* — **EBIS Business Techschool**.

## Team
- **Miguel Antonio Blanco Salcedo** — [@mikews93](https://github.com/mikews93)
- **Álvaro Augusto De Marco Neto** — [@ironeto](https://github.com/ironeto)

## Flow (matches the Core contract)

1. **Upload** a product photo + a short description and pick the **target markets** (ISO3 countries).
2. **Identify** — `POST /catalog/identify-image` runs a vision LLM and returns the
   identified product plus, per country, the curated search vocabulary and the
   ranked *reference-market candidates*.
3. **Review & edit** — the user confirms/corrects every field (name, brand,
   category, price, per-country search terms, reference candidates) before any
   paid data collection runs. This is the human-curation gate the Core is designed around.
4. **Analyze** — `POST /analyze` (202 Accepted) kicks off the background pipeline:
   ensure data freshness → Cap. 4 indicators → Cap. 5 MOS (per country).
5. **Report** — the app polls `GET /analyze/{request_id}` and renders the MOS
   ranking, each country's interpretation band, and the LLM business narrative.

## Setup

```bash
cd web
npm install
cp .env.example .env    # PUBLIC_API_BASE=http://localhost:8004
npm run dev             # http://localhost:4321
```

The Core must be running on `PUBLIC_API_BASE` (default `http://localhost:8004`)
with CORS allowing the dev origin (`http://localhost:4321`).

Convenience targets from the repo root: `make install`, `make dev`, `make build`, `make preview`.

## Backend contract (`web/src/lib/api.ts`)

- `POST /catalog/identify-image` — `{ image_base64, image_media_type, hint_text, countries }`
- `POST /analyze` — the confirmed identify-image fields + `countries` → `{ request_id, status }`
- `GET /analyze/{request_id}` — poll until `status == "done"` → `{ result: MosResult[], explanation, ... }`

## Prototypes

Clickable HTML prototypes (kept as design references):

- **[`marketmind-app.html`](marketmind-app.html)** — the original product UI concept.
- **[`marketmind-plan.html`](marketmind-plan.html)** — the architecture & plan one-pager.

## Tech

| Layer | Choice |
|---|---|
| Frontend | **Astro + View Transitions API** |
| State/flow | client-side (static output; dynamic routes resolved client-side) |
| Backend | **marketmind-orchestrator** (separate repo/service, FastAPI) — o agente é a porta de entrada desde 21/09/2026; ele chama o `marketmind-scoring` (antes `marketmind-core`), que é o motor de método. Em dev, `/api` no ingress vai ao orquestrador e `/scoring` ao scoring. |
