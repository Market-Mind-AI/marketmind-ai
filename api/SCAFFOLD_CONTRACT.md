# MarketMind AI — Scaffold Contract

Authoritative architecture + file-tree contract for the whole project. The
`domain/` and `application/` layers below are **already authored and importable**
(stdlib-only, dependency-rule clean). Everything under `infrastructure/`, plus
`web/`, `infra/`, and root files, is the planned surface for downstream agents.

## Architecture

DDD + Clean Architecture + Hexagonal (ports & adapters). **The dependency rule
is absolute: infrastructure -> application -> domain.**

- **domain/** — pure business logic. Python standard library ONLY (no pydantic,
  fastapi, sqlalchemy, anthropic, ...). Importable & unit-testable with zero
  installed deps.
- **application/** — use cases + outbound ports (`typing.Protocol`) + DTOs.
  Framework-free (stdlib + domain only). The `AnalyzeProductUseCase` orchestrates
  the pipeline in plain async Python (extract -> store -> enrich fan-out via
  `asyncio.gather` -> score -> embed+upsert+persist -> geo-rank -> report ->
  persist), emitting progress through the `ProgressPublisher` port. LangGraph is
  an intentionally-deferred OPTIONAL future infra orchestrator (docstring TODO).
- **infrastructure/** — adapters implementing the ports, the DI composition root,
  and the FastAPI inbound adapter. The ONLY layer allowed third-party frameworks.

Package root: `marketmind` (src layout: `api/src/marketmind/...`). Python 3.12.
Fakes-by-default: the whole app runs OFFLINE end-to-end with no external services
or API keys. Real adapters are stubs (TODO / `NotImplementedError`) selected via
settings. Default settings = all fakes.

## Full planned file tree

```
marked-mind/
├── README.md                       # exists — DO NOT TOUCH
├── .gitignore                      # exists — DO NOT TOUCH
├── marketmind-app.html             # exists — DO NOT TOUCH
├── marketmind-plan.html            # exists — DO NOT TOUCH
├── docs/                           # exists — DO NOT TOUCH
│   ├── architecture-plan.md
│   └── proposal.md
├── api/
│   ├── SCAFFOLD_CONTRACT.md        # this file
│   ├── pyproject.toml              # PEP 621 + uv; deps pinned (see below)
│   ├── README.md
│   ├── .env.example
│   ├── .importlinter                # import-linter contracts enforcing layers
│   ├── src/
│   │   └── marketmind/
│   │       ├── __init__.py                          # AUTHORED
│   │       ├── main.py                              # TODO: uvicorn entrypoint -> create_app()
│   │       ├── domain/                              # AUTHORED (stdlib only)
│   │       │   ├── __init__.py
│   │       │   ├── shared/
│   │       │   │   ├── __init__.py
│   │       │   │   └── errors.py
│   │       │   ├── model/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── identifiers.py
│   │       │   │   ├── status.py
│   │       │   │   ├── product.py
│   │       │   │   ├── enrichment.py
│   │       │   │   ├── scoring.py
│   │       │   │   ├── report.py
│   │       │   │   ├── embedding.py
│   │       │   │   └── analysis.py
│   │       │   ├── services/
│   │       │   │   ├── __init__.py
│   │       │   │   └── mos_calculator.py
│   │       │   └── events/
│   │       │       ├── __init__.py
│   │       │       └── events.py
│   │       ├── application/                         # AUTHORED (stdlib + domain)
│   │       │   ├── __init__.py
│   │       │   ├── dto.py
│   │       │   ├── errors.py
│   │       │   ├── ports/
│   │       │   │   ├── __init__.py
│   │       │   │   └── ports.py
│   │       │   └── use_cases/
│   │       │       ├── __init__.py
│   │       │       ├── analyze_product.py
│   │       │       └── get_analysis.py
│   │       └── infrastructure/                      # TODO (downstream agents)
│   │           ├── __init__.py
│   │           ├── api/
│   │           │   ├── __init__.py
│   │           │   ├── app.py                       # create_app() -> FastAPI
│   │           │   ├── schemas.py                   # pydantic v2 request/response
│   │           │   ├── sse.py                       # SSE helper over ProgressPublisher
│   │           │   └── routers/
│   │           │       ├── __init__.py
│   │           │       ├── analyses.py
│   │           │       └── health.py
│   │           ├── config/
│   │           │   ├── __init__.py
│   │           │   ├── settings.py                  # pydantic-settings
│   │           │   └── di.py                        # composition root
│   │           ├── persistence/
│   │           │   ├── __init__.py
│   │           │   ├── sqlalchemy_models.py
│   │           │   ├── sqlalchemy_analysis_repository.py
│   │           │   ├── in_memory_analysis_repository.py
│   │           │   ├── pgvector_store.py
│   │           │   └── in_memory_vector_store.py
│   │           ├── connectors/                      # MarketSignalProvider + GeoMarketRanker
│   │           │   ├── __init__.py
│   │           │   ├── fake.py
│   │           │   ├── dataforseo_trends.py
│   │           │   ├── world_bank_macro.py
│   │           │   └── ebay_marketplace.py
│   │           ├── llm/
│   │           │   ├── __init__.py
│   │           │   ├── fake.py
│   │           │   ├── claude_extractor.py
│   │           │   └── claude_report.py
│   │           ├── embeddings/
│   │           │   ├── __init__.py
│   │           │   ├── fake.py
│   │           │   └── cohere_embeddings.py
│   │           ├── storage/
│   │           │   ├── __init__.py
│   │           │   ├── local_filesystem.py
│   │           │   └── s3_storage.py
│   │           ├── pdf/
│   │           │   ├── __init__.py
│   │           │   ├── weasyprint_renderer.py
│   │           │   └── html_renderer.py
│   │           └── progress/
│   │               ├── __init__.py
│   │               └── in_memory.py
│   └── tests/                       # TODO: pytest (domain unit tests, use-case tests, api tests)
│       ├── __init__.py
│       ├── domain/
│       ├── application/
│       └── infrastructure/
├── web/                             # TODO: frontend (consumes the API + SSE)
└── infra/                           # TODO: docker-compose (postgres+pgvector), Dockerfiles, IaC
```

See the returned CONTRACT (the agent's final message) for exact signatures and
infrastructure adapter constructor surfaces. That CONTRACT is the binding source
of truth.
