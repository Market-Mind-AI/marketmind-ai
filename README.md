# MarketMind AI

> **Framework de Inteligencia Comercial basado en IA Generativa** para identificar oportunidades de mercado a partir de datos públicos globales.

MarketMind AI turns a single product (images + a free-text description) — or a whole catalog — into an **explainable market-opportunity report**: a Market Opportunity Score (MOS), the best target markets, suggested pricing, and the optimal launch window, every claim backed by a cited public data source.

Final project (TFM) for the *Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa* — **EBIS Business Techschool**.

## Team
- **Miguel Antonio Blanco Salcedo** — [@mikews93](https://github.com/mikews93)
- **Álvaro Augusto De Marco Neto** — [@ironeto](https://github.com/ironeto)

## What it does

1. **Upload** product images + a description (the hero flow), or a CSV/Excel catalog (batch mode).
2. **Extract** product attributes with a vision LLM (no forms to fill).
3. **Enrich** each product with public global signals — demand trends, macro/geographic data, and a marketplace signal.
4. **Score** a transparent, pure-Python **Market Opportunity Score (MOS)**.
5. **Report** explainable recommendations (markets · pricing · timing) with **live streaming progress**, an inline result, a **downloadable PDF**, and a **shareable link**.

## Architecture (at a glance)

A deterministic enrichment **DAG** with two LLM reasoning steps — *not* an autonomous agent swarm.

| Layer | Choice |
|---|---|
| Frontend | **Astro + View Transitions API** (app-like UX) |
| API | **FastAPI** (async) + **SSE** live progress |
| Orchestration | **LangGraph** `StateGraph` |
| Vision / extraction | **Claude Haiku 4.5** |
| Report generation | **Claude Sonnet 4.6** |
| Scoring | Pure **Python** (winsorize → min-max → weighted sum) |
| Data | World Bank · IMF · DataForSEO (Trends) · eBay Browse |
| Stores | PostgreSQL (+ pgvector) · object storage · ChromaDB (optional) |
| Report → PDF | WeasyPrint |
| Infra | **Terraform** (cloud-agnostic) · docker-compose for local |

Full detail: **[docs/architecture-plan.md](docs/architecture-plan.md)**. Original proposal: **[docs/proposal.md](docs/proposal.md)**.

## Prototypes

Clickable HTML prototypes (open in a Chromium browser for the View Transitions):

- **[`marketmind-app.html`](marketmind-app.html)** — the product UI: single-product upload → live analysis → report, plus the CSV batch mode with a sortable ranked table.
- **[`marketmind-plan.html`](marketmind-plan.html)** — the architecture & plan as a visual one-pager.

## Planned structure

```
marketmind-ai/
├── api/        # FastAPI + LangGraph pipeline, connectors, MOS engine
├── web/        # Astro frontend (View Transitions)
├── infra/      # Terraform modules + docker-compose
├── docs/       # architecture plan, proposal
└── *.html      # interactive prototypes
```

## Status

🚧 Early stage — architecture and prototypes defined; implementation kicking off (see the roadmap in the architecture plan).
