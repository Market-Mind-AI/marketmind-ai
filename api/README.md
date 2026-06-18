# MarketMind AI — API

Generative-AI commercial-intelligence platform (Master's thesis MVP).

Given product **images** + a free-text **description**, the pipeline runs:

```
extract attributes (vision LLM)
  -> enrich with public signals (trends / macro·geo / marketplace, fanned out concurrently)
  -> compute a transparent Market Opportunity Score (MOS)
  -> embed + persist + find comparables
  -> generate an explainable report (markets / pricing / timing, with citations)
  -> deliver inline + PDF + shareable link
```

A secondary CSV batch mode runs the same pipeline over rows.

This package is the backend (`marketmind`), Python 3.12, src layout
(`api/src/marketmind/...`).

---

## Run it offline (no API keys, no external services)

The default configuration (`provider_mode=fake`) wires **in-memory / fake
adapters** for every port, so the whole app runs end-to-end with nothing
installed beyond the Python deps.

```bash
cd api
cp .env.example .env        # optional — defaults already select all fakes
uv sync                     # create the venv + install deps (incl. dev group)
make run                    # uvicorn marketmind.main:app --reload
```

Then:

- API docs: <http://localhost:8000/docs>
- Health:   <http://localhost:8000/health>

Submit an analysis (multipart):

```bash
curl -F "description=hand-poured soy candle, amber jar, minimalist label" \
     -F "images=@/path/to/photo.jpg" \
     http://localhost:8000/analyses
# -> { "id": "..." }, then:
curl http://localhost:8000/analyses/<id>
curl -N http://localhost:8000/analyses/<id>/events        # SSE progress
curl http://localhost:8000/analyses/<id>/report.pdf -o report.pdf
```

### With Docker

```bash
cd api
docker build -t marketmind-api .
docker run --rm -p 8000:8000 marketmind-api      # offline/all-fakes by default
```

---

## Architecture — DDD + Clean Architecture + Hexagonal

**The dependency rule is absolute: dependencies point inward only.**

```
infrastructure  ──►  application  ──►  domain
   (adapters)        (use cases)     (pure logic)
```

```
api/src/marketmind/
├── domain/          # pure business logic — STDLIB ONLY (no third-party imports)
│   ├── model/       #   value objects + Analysis entity (frozen dataclasses)
│   ├── services/    #   MosCalculator (transparent, deterministic scoring)
│   ├── events/      #   domain events
│   └── shared/      #   domain errors
├── application/     # use cases + outbound PORTS (typing.Protocol) + DTOs
│   ├── ports/       #   AnalysisRepository, ProductAttributeExtractor, …
│   ├── use_cases/   #   AnalyzeProductUseCase, GetAnalysisUseCase
│   ├── dto.py       #   commands + read-model views
│   └── errors.py
└── infrastructure/  # the ONLY layer allowed to import frameworks
    ├── persistence/ #   in-memory + SQLAlchemy/pgvector adapters
    ├── connectors/  #   fake + real market-signal providers / geo ranker
    ├── llm/         #   fake + Claude (Anthropic SDK) extractor & report gen
    ├── embeddings/  #   fake + Cohere
    ├── storage/     #   local filesystem + S3
    ├── pdf/         #   HTML fallback + WeasyPrint
    ├── progress/    #   in-memory SSE publisher
    ├── config/      #   pydantic-settings + DI composition root (Container)
    └── api/         #   FastAPI app, routers, schemas, SSE adapter
```

- **`domain/`** depends on nothing but the standard library — importable and
  testable with zero installed dependencies.
- **`application/`** is framework-free (stdlib + domain only). The
  `AnalyzeProductUseCase` orchestrates the pipeline in plain async Python
  (`asyncio.gather` for the enrichment fan-out) and emits progress through the
  `ProgressPublisher` port. A future LangGraph orchestrator is intentionally
  deferred to an optional infrastructure adapter to keep the use case
  framework-agnostic.
- **`infrastructure/`** implements the ports and is the only layer permitted to
  import FastAPI, SQLAlchemy, the Anthropic/Cohere SDKs, httpx, etc.

The rule is enforced in CI by **import-linter** (`make arch`):
`domain` may import nothing outward; `application` may import `domain` only;
both forbid third-party frameworks.

### Request flow

```
POST /analyses (multipart: description + images)
  → routers/analyses → AnalyzeProductCommand → AnalyzeProductUseCase.handle
      → ProductAttributeExtractor.extract            (step: extracting)
      → asyncio.gather(MarketSignalProvider.fetch …)  (step: enriching)
      → MosCalculator.score                           (step: scoring)
      → EmbeddingModel.embed + VectorStore.upsert      (step: embedding)
      → ReportGenerator.generate (+ comparables)       (step: reporting)
      → AnalysisRepository.save                         (step: completed)
  ← AnalysisId

GET  /analyses/{id}          → GetAnalysisUseCase → AnalysisView
GET  /analyses/{id}/events   → SSE stream of ProgressPublisher events
GET  /analyses/{id}/report.pdf → PdfRenderer
```

---

## Where to plug in real adapters

Set `MARKETMIND_PROVIDER_MODE=real` (and provide credentials) and the DI
composition root (`infrastructure/config/di.py`) selects the real adapter for
each port. Real adapters live alongside their fakes:

| Port | Fake (default) | Real adapter | Credential(s) |
|------|----------------|--------------|---------------|
| `ProductAttributeExtractor` | `llm/fake.py` | `llm/claude_extractor.py` (Claude `claude-haiku-4-5-20251001`) | `MARKETMIND_ANTHROPIC_API_KEY` |
| `ReportGenerator` | `llm/fake.py` | `llm/claude_report.py` (Claude `claude-sonnet-4-6`) | `MARKETMIND_ANTHROPIC_API_KEY` |
| `EmbeddingModel` | `embeddings/fake.py` | `embeddings/cohere_embeddings.py` | `MARKETMIND_COHERE_API_KEY` |
| `MarketSignalProvider` (TREND) | `connectors/fake.py` | `connectors/dataforseo_trends.py` | `MARKETMIND_DATAFORSEO_LOGIN/PASSWORD` |
| `MarketSignalProvider` (GROWTH) | `connectors/fake.py` | `connectors/world_bank_macro.py` | — |
| `MarketSignalProvider` (CONSUMER) | `connectors/fake.py` | `connectors/ebay_marketplace.py` | `MARKETMIND_EBAY_APP_ID` |
| `AnalysisRepository` | `persistence/in_memory_analysis_repository.py` | `persistence/sqlalchemy_analysis_repository.py` | `MARKETMIND_DATABASE_URL` |
| `VectorStore` | `persistence/in_memory_vector_store.py` | `persistence/pgvector_store.py` | `MARKETMIND_DATABASE_URL` |
| `ObjectStorage` | `storage/local_filesystem.py` | `storage/s3_storage.py` | (S3 client) |
| `PdfRenderer` | `pdf/html_renderer.py` | `pdf/weasyprint_renderer.py` (`pdf` extra) | — |

Real adapters that talk to external APIs ship as stubs (clear `TODO` /
`NotImplementedError`); flesh them out to go live. Persistence is also toggled
by `MARKETMIND_USE_IN_MEMORY_PERSISTENCE` (default `true`).

---

## Configuration (env, prefix `MARKETMIND_`)

See [`.env.example`](./.env.example) for the full list with defaults. Key vars:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MARKETMIND_PROVIDER_MODE` | `fake` | `fake` = fully offline; `real` = use real adapters |
| `MARKETMIND_USE_IN_MEMORY_PERSISTENCE` | `true` | Bypass Postgres/pgvector |
| `MARKETMIND_DATABASE_URL` | `postgresql+asyncpg://…` | Async Postgres DSN |
| `MARKETMIND_ANTHROPIC_API_KEY` | _(none)_ | Claude extraction + report |
| `MARKETMIND_COHERE_API_KEY` | _(none)_ | Cohere embeddings |
| `MARKETMIND_EXTRACTION_MODEL` | `claude-haiku-4-5-20251001` | Vision/extraction model |
| `MARKETMIND_REPORT_MODEL` | `claude-sonnet-4-6` | Report generation model |
| `MARKETMIND_EMBEDDING_MODEL` | `embed-english-v3.0` | Embedding model |
| `MARKETMIND_EMBEDDING_DIMENSIONS` | `1024` | Embedding vector size |
| `MARKETMIND_STORAGE_ROOT` | `./.data/uploads` | Local object storage root |
| `MARKETMIND_CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `MARKETMIND_HOST` / `MARKETMIND_PORT` | `0.0.0.0` / `8000` | Bind address |
| `MARKETMIND_LOG_LEVEL` | `INFO` | Log level |

---

## Developer tasks

```bash
make install     # uv sync (deps + dev group)
make run         # run the API with reload
make test        # pytest (asyncio_mode=auto, pythonpath=src)
make lint        # ruff check
make typecheck   # mypy (strict-ish)
make arch        # import-linter — enforce the dependency rule
make fmt         # ruff format + --fix
make check       # lint + typecheck + arch + test
```

---

## License

MIT — academic / thesis use.
