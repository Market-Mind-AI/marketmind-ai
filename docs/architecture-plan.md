# MarketMind AI — Architecture & Build Plan (TFM)

## Context

This is the architecture plan for **MarketMind AI**, the final Master's project (TFM) for the *Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa* (EBIS), built by 2 students (Alvaro De Marco, Miguel Blanco). The goal: a generative-AI commercial-intelligence platform that ingests a product catalog (CSV/Excel + optional images), enriches each product with **public global data sources**, computes a **Market Opportunity Score (MOS)**, and generates **explainable** commercial recommendations (which markets/regions, pricing, timing). The team also wants **Terraform** so the infra is cloud-agnostic, not locked to one provider.

This plan answers the three things you asked: (1) a concrete end-to-end architecture, (2) which data sources are actually best — including a blunt verdict on **Amazon** — and (3) whether to let users upload images and have an LLM extract product info (yes — it's your headline gen-AI feature).

It was produced from a multi-agent research pass (9 parallel research tracks → design synthesis → adversarial feasibility review). The guiding principle from that review: **the easy failure mode for this TFM is over-scope, not under-scope.** So this plan separates the *full architecture vision* (what you write up and design for) from a *disciplined MVP build scope* (what 2 people can actually ship, validate, and defend in one semester).

### Decisions locked (from your answers)
- **Data budget:** free-tier first. Free public sources carry the MVP; paid sources are optional pluggable connectors switched on only for the final demo.
- **Deployment:** local-first (docker-compose) for demos + **Terraform written and cloud-agnostic** (provable on one cloud). A live cloud deploy is an optional stretch, not required.
- **Image → attribute extraction:** include it, but scoped. Build it well as a real feature.
- **LLM strategy:** hybrid — cheap model for high-volume extraction, top model for the explainable reports.
- **Primary UX (NEW — the hero flow):** a **single-product interactive flow** is the main experience — the user uploads product images + writes a free-text **description**, the API reviews it, and an explainable report renders **inline on the same page** with a **download** button. Bulk CSV/Excel becomes a secondary *batch mode* (same pipeline, fanned over rows) so the proposal's catalog-ingestion objective still holds.
- **Form input:** images + a free-text **description only** — the vision LLM infers category and attributes; no structured fields required.
- **Progress UX:** **live step-by-step progress** streamed from the API (Server-Sent Events) during the ~15–60 s analysis, so the wait feels intelligent rather than a blind spinner.
- **Report deliverable:** a **branded PDF** download **plus a shareable, revisitable web link** (`/r/{slug}`).
- **Frontend stack (NEW):** **Astro + the View Transitions API** for an app-like, morphing UI (the product thumbnail/title morph across upload → analyzing → report). This **replaces Streamlit** as the primary UI — a deliberate, UX-driven deviation to call out and justify in the thesis.

---

## 1. The single most important design decision

**This is a deterministic enrichment DAG with two genuine LLM reasoning steps — not an autonomous multi-agent swarm.** Build it as a LangGraph `StateGraph`, keep the MOS arithmetic in pure, auditable Python, and reserve LLM calls for the two places they add real value:

1. **Vision attribute extraction** (image/description → structured product attributes) — *cheap model*.
2. **Explainable report generation** (synthesize signals into a cited recommendation) — *top model*.

Everything else (connectors, scoring, geo-ranking) is plain Python. This keeps the system debuggable, near-zero-cost, and academically defensible — and it's the decision that makes the project finishable by 2 people.

---

## 2. End-to-end data flow

```
[1] Upload        HERO FLOW: web UI — drag product images + write a description -> POST /analyses
       (single      (batch mode: CSV/Excel -> POST /catalogs runs the SAME pipeline, fanned over rows)
        product)     │  images -> object storage ; analysis row -> Postgres ; runs via BackgroundTask
         │           └─ UI opens SSE  GET /analyses/{id}/stream  (live step-by-step progress)
         ▼
[2] Ingest        IngestionNode  (pandas/openpyxl + Pydantic validation) -> normalized products[]
         ▼
[3] Extract       AttributeExtractionNode  (Claude Haiku 4.5 vision, structured output)
       attributes   category / material / color / use-case / keywords + per-field confidence
                    text-only fallback when no image  (Ollama Qwen2.5-VL fallback in dev)
         ▼
[4] Enrich        EnrichmentFanOut  (LangGraph Send API — parallel scatter/gather, 7-day cache)
       (parallel)   ├─ TrendsConnector        (DataForSEO Trends)            -> Demand/Trend
                    ├─ MacroGeoConnector       (World Bank + IMF DataMapper)  -> Growth + Geographic
                    └─ MarketplaceConnector    (eBay Browse API, free)        -> Marketplace demand
                    (optional, flag-gated: Reddit / Comtrade — see §10)
         ▼
[5] Score         MOSScoringNode  (PURE PYTHON: winsorize -> min-max -> weighted sum)
         ▼
[6] Geo match     GeoMatchingNode  (rank countries from WB GNI-PPP + e-commerce penetration + eBay)
         ▼
[7] Report        ReportNode  (Claude Sonnet 4.6 + cited Pydantic schema, PER CATEGORY
                    with 2-3 per-product drill-downs)
         ▼
[8] Deliver       -> persist analysis (Postgres) ; SSE emits "report_ready"
                    -> report renders INLINE on the same page (MOS gauge + factor bars + market map)
                    -> download branded PDF (WeasyPrint)  +  shareable link  /r/{slug}
```

LangGraph checkpointing (`SqliteSaver` local / `PostgresSaver` cloud) sits under the graph so a rate-limit failure at product 300 *resumes* rather than restarts — this is the genuine reason to use LangGraph over a plain `for` loop.

---

## 3. Component architecture

| Layer | Choice | Why |
|---|---|---|
| **Frontend** | **Astro + View Transitions API** | App-like morphing transitions (upload → analyzing → report) with multi-page simplicity and strong performance — no SPA weight. Talks to FastAPI; the browser `EventSource` consumes the SSE stream for live progress. Deliberate swap from the proposal's Streamlit — see §9. |
| **API** | FastAPI (async) | Async fits the parallel connector fan-out; Pydantic models are the shared contract with LangGraph state; free OpenAPI docs. |
| **Orchestration** | LangGraph `StateGraph` | Fixed DAG, parallel `Send`, conditional fallback edges, checkpoint/resume. CrewAI/AutoGen explicitly rejected (role/debate abstractions don't fit a pipeline). |
| **LLM nodes** | 2 only | Haiku 4.5 (vision/normalization) + Sonnet 4.6 (report). Everything else is typed Python over shared state. |
| **Connectors** | Adapter classes behind a `Connector` interface (`fetch(product)->dict`, `is_available()`) | Swap DataForSEO ↔ official Trends API later without touching scoring. New sources = new adapter only. |
| **Scoring engine** | Pure Python + NumPy / scikit-learn `MinMaxScaler` | Deterministic, unit-testable, reproducible — mandatory for the methodology chapter. No LLM in the arithmetic. |
| **Relational store** | PostgreSQL 16 (+ pgvector ready) | Products, enrichment cache, MOS results, LangGraph checkpoints — one DB. |
| **Vector store** | ChromaDB (embedded, optional) | Honors the proposal, zero infra. Scope = report grounding / comparable-product retrieval only. *Lightly used in MVP* (empty on first run); pgvector is the cloud migration path. |
| **Object storage** | S3-compatible via `boto3` + `S3_ENDPOINT_URL` | Identical code across S3/GCS/Azure Blob/SeaweedFS. |
| **Async work** | FastAPI `BackgroundTasks` + status row in Postgres | A batch academic tool doesn't need Celery+Redis. (Celery/Redis documented as the *scale-out* path for the thesis's "future scalability" section, not built.) |
| **Caching** | Postgres cache table, 7-day TTL | Trend/macro data changes weekly at most; cuts 80–90% of repeat API calls → re-demo ≈ €0. |
| **Secrets** | `.env` (local) → K8s `Secret` / HCP Vault free tier (cloud) | Cloud-agnostic, no per-cloud secret-manager lock-in. |
| **LLM provider switch** | `LLM_PROVIDER` env var | Ollama + Qwen2.5-VL locally for free dev; Claude API for the demo. |
| **Live progress** | SSE via `sse-starlette` | The pipeline emits an event as each node finishes → the UI shows real step-by-step progress, not a blind spinner. Map LangGraph `astream` events → SSE. |
| **Report → PDF** | WeasyPrint (HTML/CSS → PDF) | The report renders as styled HTML once; the *same* HTML becomes the downloadable PDF. One template, two outputs. |
| **Report store + share** | Postgres row + `slug` route `/r/{slug}` | Each analysis is persisted; a short slug gives a public, revisitable, shareable report URL. |

---

## 4. Data source plan (free-first) — and the Amazon verdict

### Tier 0 — always free, the MVP runs entirely on this
- **World Bank Indicators API** — no key, CC-BY 4.0. GDP, GNI/PPP, population, internet/e-commerce penetration.
- **IMF DataMapper API** — no key. *Forward-looking* GDP growth (`NGDP_RPCH`) — the growth signal World Bank lacks.
- **OECD SDMX-JSON** — no key. PPP + consumer indicators (supplement; only 38 countries).
- **eBay Browse API** — free, 5k calls/day, official + citable. The cleanest legitimate marketplace demand signal — make it a first-class connector.

### Tier 1 — tiny one-time spend, switch on for the final demo
- **DataForSEO** — a single **~$50 deposit**, pay-as-you-go, no monthly fee. Covers **Trends** (~$0.001/task), **keyword search volume**, and **Amazon SERP/BSR**. This is the workhorse and the **legitimate replacement for `pytrends`** (which is archived/unreliable/ToS-risky — do not ship it; dev-only fallback at most). A 500-product run costs single-digit dollars. *Note:* technically a small paid connector, but ~$50 total reads as "free-tier first" in practice; until you need real Trends data, Tier-0 sources carry the build.

### Tier 2 — optional, disabled by default
- **Keepa (€49/mo)** — multi-year Amazon BSR/price history. Use for **~1 month as the MOS validation ground truth** (internal benchmark), not as a public-facing data source.
- **Exploding Topics / Glimpse** — early-trend detection / absolute search volume. Nice-to-have upgrades to the Trend factor.
- **Reddit (PRAW free tier)** — *gated* (pre-approval required since Nov 2025) and rate-limited (~100 req/day). Keep **optional/best-effort, never on the critical path**.

### Source → MOS factor mapping (MVP core in **bold**)
| MOS factor | Primary (free / cheap) | Optional upgrade |
|---|---|---|
| **Trend / Demand (30%)** | **DataForSEO Trends** (12-mo interest slope) | Exploding Topics; Glimpse |
| **Growth (25%)** | **IMF `NGDP_RPCH`** + WB category proxies | Euromonitor/Statista *if your university library has it* |
| **Geographic (20%)** | **WB GNI-PPP + e-commerce penetration + eBay listing density** | UN Comtrade/WITS by HS6 (deferred — see §10) |
| Seasonality (15%) | STL/Prophet over Trends series *(see §7 caveat)* | Pinterest Trends (free) |
| Consumer interest (10%) | DataForSEO keyword volume | Reddit (optional); Amazon reviews via Keepa |

### Amazon verdict — direct answer to your question
You asked specifically whether Amazon exposes product insights. **Amazon does not give third parties market intelligence.** Concretely:
- **SP-API — NO.** Scoped to a seller's *own* data, and now ~**$1,400/yr** for third-party developers. Not viable.
- **Product Advertising API (PA-API) — NO.** Requires qualifying affiliate sales (cold-start you can't clear), and its data-use clause **explicitly prohibits using the data to train/improve LLMs** — a direct legal conflict with this thesis. Disqualified on its own terms.
- **Scraping Amazon — NO.** ToS violation; presenting scraped Amazon data in a thesis defense is an avoidable academic-integrity flag.
- **YES → DataForSEO Amazon SERP/BSR** — legitimate data reseller, no seller account, pay-as-you-go, citable. Your Amazon-adjacent demand signal.
- **YES → Keepa** — for BSR/price *history*, used as **validation ground truth** (internal), not displayed publicly.
- **YES → eBay Browse API** — the academically cleanest official marketplace signal.

**Bottom line for the thesis:** the *reasoning* about why Amazon's official channels are off-limits is itself a strong, defensible section of your methodology. Use DataForSEO + Keepa + eBay; cite the Amazon analysis as a deliberate, justified design choice.

---

## 5. Image → attribute extraction (your headline feature)

**Yes — build it.** It's the strongest "generative AI" moment in the demo, it directly fulfills the TFM's vision-LLM objective, and it's cheap (Haiku 4.5 vision ≈ ~$0.0014/image → 500 images < ~$1; verify current pricing). It also genuinely improves enrichment: user CSV categories are inconsistent, and vision + a standard taxonomy normalizes them.

Design:
- **Model:** Claude Haiku 4.5 (vision), structured output (tool-use / structured-output API) → a fixed Pydantic schema: `category`, `subcategory`, `material`, `color`, `style`, `key_features[]`, `suggested_keywords[]`, plus a **per-field `confidence` (0–1)**.
- **Taxonomy mapping:** map to Google Product Taxonomy or Amazon browse-node style categories (a static lookup) for consistent enrichment keys.
- **Guardrails:** resize images to **≤1024px long edge** before sending (controls cost); PNG for label/text images, JPEG-85 otherwise; flag low-confidence fields for review.
- **Honest caveats (from the review):** (a) LLM self-reported confidence is poorly calibrated — spot-check before building hard control flow on a `<0.6` threshold; (b) `pyzbar` barcode reading is best-effort only — hero catalog photos rarely show the EAN/UPC, so don't position it as a load-bearing "deterministic" win.

---

## 6. LangGraph design + LLM strategy (hybrid)

- **Graph (≈7 nodes):** `ingest → extract_attributes → [enrich_fanout via Send] → merge → score_mos → geo_match → generate_report → package`. Conditional edges only for: no-image → text-only extraction; connector failure → impute + flag.
- **Shared state:** one `TypedDict` with `add`-reducer lists for the append-style nodes (extraction, enrichment, errors).
- **LLM tiers (your hybrid choice):**
  - **Haiku 4.5** — bulk vision extraction, attribute normalization, keyword suggestion (~$1/$5 per MTok; verify).
  - **Sonnet 4.6** — report generation only, **per category** (~$3/$15 per MTok; verify). *Resolved fork:* per-category synthesis (not per-product × 500) — cheaper, faster, and the more interesting deliverable; add 2–3 per-product drill-downs for the demo.
  - **Opus 4.8 — avoid.** No task here needs it.
  - **Local dev:** Ollama + Qwen2.5-VL behind `LLM_PROVIDER` → develop for free, demo on Claude API.
  - Use **structured outputs** everywhere (guaranteed schema, no parse retries); use **prompt caching** on the shared system prompt + catalog context for 60–90% savings on re-runs.
- Full 500-product run with caching ≈ a few dollars one-time.

---

## 7. MOS computation + validation

**Frame the methodology chapter on the OECD/JRC *Handbook on Constructing Composite Indicators* 10-step framework** — examiners recognize it instantly and it maps 1:1 to your sections.

**Per sub-indicator pipeline:** winsorize at 1st/99th percentile → min-max to [0,1] → weighted sum. Treat Google Trends `0` as **missing, not zero**. Because aggregation is linear, explainability is *exact*: `contribution_i = w_i · score_i` → render as a per-product horizontal **stacked bar** in Streamlit.

**Recommended approach to the factor set (this is itself a thesis contribution):**
1. **Implement the engine config-driven** so weights and the factor list live in config.
2. Start from the **proposed 5 factors** (Trend 30 / Growth 25 / Geographic 20 / Seasonality 15 / Consumer 10).
3. Run a **redundancy analysis** (pairwise Pearson across sub-scores). The review flagged a real problem: **Trend, Seasonality, and keyword-volume all derive from the same DataForSEO signal** (~55% of the score is shared-source) — plus Trend↔Growth proxy demand at different horizons. Report this honestly.
4. Present a **validated 3-factor MOS** as the recommended final score: **Demand Trajectory (~45%) + Market Attractiveness/Geographic (~35%) + Marketplace Demand (~20%)**, with an **equal-weights baseline** for comparison. A clean, independent, fully-validated 3-factor score beats a 5-factor score where two factors are mostly imputed and correlated. The journey *proposed → analyzed → validated* is exactly what earns marks.

**Seasonality caveat:** STL/Prophet seasonal decomposition wants ≥24 months (2 cycles); 12 months barely identifies the seasonal component. Either pull longer Trends history (DataForSEO can) or **drop Seasonality from the composite and surface it as a separate qualitative flag** — don't claim a decomposition you can't statistically support.

**Validation (do ONE properly; list the rest as future work):**
- **Primary — Keepa BSR Spearman.** Sample 50–80 products across 3–5 categories; compute **Spearman ρ** between MOS rank and inverse-BSR rank. Report ρ, p-value, 95% CI. **ρ > 0.35, p < 0.05** is a defensible positive result. (BSR is ordinal/category-relative — treat as a rank proxy, never absolute sales.) This single number converts "we invented a score" into a defensible contribution.
- **Cheap secondary (recommended):** equal-weights baseline comparison + a basic ±25% weight sensitivity check.
- **Future work (don't build now):** COINr/Sobol indices, AHP expert elicitation, predictive-validity held-out window, category-adaptive weights.

---

## 8. Cloud-agnostic Terraform / IaC

**Portability boundary = the container / Kubernetes API.** Everything inside the cluster (same images, same manifests) is portable; only cluster provisioning, managed Postgres, and IAM are provider-specific and swapped via `tfvars`.

**Honest framing for the thesis:** claim **"cloud-portable IaC," not "multi-cloud-live."** You satisfy the "cloud-agnostic Terraform" objective by writing **modular Terraform with provider abstraction and deploying it once** (or just demonstrating `terraform plan`) **plus a written portability analysis** — *not* by actually standing up a second cloud. A 3-cloud portability proof is months of infra work that earns ~30 seconds of examiner attention. **Do not build Phase 3.**

**Repo layout:**
```
infra/
├── modules/
│   ├── compute/          # k8s-cluster OR container-on-VM; submodules: aws/ gcp/ azure/
│   │                     #   all export identical outputs (endpoint, ca_cert, ...)
│   ├── postgres/         # rds | cloud_sql | azurerm_postgresql (+ pgvector)
│   ├── object-storage/   # s3 | gcs | azure_blob (S3-compatible iface)
│   ├── networking/       # vpc | vnet
│   └── secrets/          # kubernetes_secret | hcp_vault
├── environments/
│   ├── local/            # docker-compose only, NO terraform
│   └── dev/              # one cloud, small/scale-to-zero nodes
├── k8s/ (or compose)     # SAME manifests across clouds — never edited on cloud switch
└── docker-compose.yml
```
Conventions: each module `main.tf / variables.tf / outputs.tf / versions.tf / README.md`; pin providers `~>`; commit `.terraform.lock.hcl`; **state backend = HCP Terraform free tier** (provider-neutral — avoids needing S3 before Terraform can make S3). Follow the **terraform-module-library** skill conventions.

**Phased deploy:**
- **Phase 1 (local, required):** one `docker-compose.yml` — FastAPI, Streamlit, Postgres+pgvector, (optional Chroma). `.env` secrets. **This is your demo and your MVP.**
- **Phase 2 (single cloud, optional/stretch):** **GKE Autopilot or Cloud Run** (scale-to-zero, $300 GCP credit) OR a single VM running docker-compose. Convert compose services → manifests. ~€0–30/mo with caching + scale-to-zero.
- **Phase 3:** **does not exist** — replaced by a written portability analysis.

---

## 9. API design + the single-product experience

**Hero flow — single product (primary):**
```
POST   /analyses                 multipart: images[] + description  -> 201 {analysis_id, slug}
GET    /analyses/{id}/stream     SSE — live pipeline progress events (one per node)
GET    /analyses/{id}            full structured report (JSON: MOS, factors, markets, citations)
GET    /analyses/{id}/report.pdf rendered branded PDF (WeasyPrint, from the report HTML)
GET    /r/{slug}                 public, shareable, revisitable report page (HTML)
POST   /analyses/{id}/reprocess  re-run with new weights / refreshed data
```
**Batch mode — bulk catalog (secondary):**
```
POST   /catalogs                 upload CSV/Excel -> 202 {job_id}  (same pipeline, fanned over rows)
GET    /catalogs/{id}/status     batch progress
GET    /catalogs/{id}/products   paginated results + MOS
GET    /healthz                  liveness
```

**The single-product experience (the hero demo):**
1. The user **drops product images and writes a free-text description** — no structured fields; the vision LLM infers category and attributes.
2. `POST /analyses` stores the images and returns immediately with `{analysis_id, slug}`; a `BackgroundTask` runs the LangGraph pipeline.
3. The page opens an **`EventSource` on `/analyses/{id}/stream`** and shows **live step-by-step progress** ("read 3 images → 7 attributes", "Google Trends +24% / 12mo", "scoring MOS", "writing report") as each node finishes — LangGraph `astream` events mapped to SSE.
4. On `report_ready`, the **report renders inline on the same page**: the MOS gauge, the factor-contribution stacked bar, recommended **markets / pricing / timing**, and a **citations** table.
5. The user **downloads a branded PDF** (`/analyses/{id}/report.pdf`, rendered from the same HTML via WeasyPrint) or **shares the link** (`/r/{slug}`, persisted and revisitable).

**Frontend — Astro + View Transitions API (decided):** The UI is an **Astro** site (static/SSR) that calls FastAPI. Astro's view transitions give the app-like feel — the **product thumbnail and title morph** across the upload → analyzing → report views and navigation is seamless — without a full SPA framework. Live progress is the browser **`EventSource`** consuming `/analyses/{id}/stream`; the report renders from `/analyses/{id}`; the PDF and `/r/{slug}` share page are server routes. This is a deliberate deviation from the proposal's Streamlit — **call it out in the thesis as a UX-driven decision** (and note the View Transitions API is itself a current, demo-worthy web capability). Mutating endpoints validate against the same Pydantic models LangGraph uses.

> **Architecture impact:** the frontend is now a separate Astro app, not a Python Streamlit page — so CORS config on FastAPI, a small `web/` Astro project alongside `api/`, and an extra container in docker-compose. The pipeline, connectors, MOS engine and API contract are unchanged.

---

## 10. Scope discipline — MVP core vs. deferred

**Core MVP (build, validate, write up):**
1. **Single-product upload** (drag images + free-text description) as the hero flow; CSV/Excel as a secondary batch mode.
2. **Image → attribute extraction (Haiku vision)** — the headline gen-AI feature; even more central now that there are no structured input fields.
3. **Three enrichment connectors:** DataForSEO Trends, World Bank + IMF, eBay Browse.
4. **Pure-Python MOS** with winsorize→min-max→weighted sum + exact additive explainability.
5. **One Sonnet report node**, cited Pydantic schema.
6. **Inline report on the same page** (MOS gauge + stacked-bar contributions + ranked markets + map) with **live SSE progress**, a **branded PDF download**, and a **shareable `/r/{slug}` link**.
7. **One validation method done properly: Keepa BSR Spearman.**
8. **One** clean modular Terraform deployment (or `plan`) + written portability analysis.

**Explicitly deferred / "future work" (say so in the thesis):**
- ❌ Multi-cloud / second Terraform provider (Phase 3) → written portability analysis instead.
- ❌ Celery + Redis → FastAPI `BackgroundTasks`.
- ❌ HS-code RAG + UN Comtrade trade-flow pillar → highest-effort, lowest-reliability subsystem (HS classification is hard, Comtrade cells are sparse). Approximate geography from WB GNI-PPP + e-commerce penetration + eBay. *Strong future-work candidate.*
- ❌ Reddit → optional/best-effort connector (gated + rate-limited).
- ❌ Seasonality as a real STL factor on 12 months → qualitative flag, or fold its weight into Trend.
- ❌ Dedicated vector DB as a service → embedded Chroma lightly used, or skip; pgvector for cloud.
- ❌ COINr/Sobol, AHP, predictive validity, category-adaptive weights → future rigor.

---

## 11. Build roadmap (2-person, mapped to thesis objectives)

| Phase | Weeks | Deliverable | Thesis objective | Owners |
|---|---|---|---|---|
| **0 — Scaffold** | 1–2 | docker-compose stack, FastAPI skeleton, Postgres+pgvector, Streamlit shell, `LLM_PROVIDER` abstraction; **week-1 spike: validate DataForSEO Trends data quality on YOUR actual test catalog** | Reproducible MVP base | A: backend/infra · B: data/LLM |
| **1 — Single-product flow + Vision** | 3–4 | Hero UI: drag-images + description form → `POST /analyses` → **live SSE progress** → AttributeExtractionNode (Haiku) + confidence (CSV batch deferred to a later sprint) | "LLM extracts product info from images/descriptions" | B leads extraction, A the UI/API/SSE |
| **2 — Enrichment** | 5–7 | 3 connectors (DataForSEO, WB+IMF, eBay) behind `Connector` iface; parallel `Send` fan-out; 7-day cache; checkpointing | "Enrich with public global data sources" | A: connectors/cache · B: trends |
| **3 — MOS engine** | 8–9 | Config-driven pure-Python scoring, winsorize+min-max, additive explainability, redundancy analysis | "Compute explainable MOS" | B: formulas · A: API surfacing |
| **4 — Geo + Report + Deliverable** | 10–11 | GeoMatchingNode; Sonnet report (cited schema); **inline report UI** (stacked bars + map); **WeasyPrint PDF** + shareable `/r/{slug}` link | "Explainable recommendations via LLM" | B: report · A: UI/PDF |
| **5 — Validation** | 12–13 | Keepa BSR Spearman (ρ, p, CI) + equal-weights baseline + 3-factor reconciliation | Methodology / scientific rigor | both |
| **6 — IaC** | 14–16 | Modular Terraform (one cloud) + portability analysis; thesis write-up | "Cloud-agnostic Terraform IaC" | A leads, B supports |

---

## 12. Top risks & mitigations
- **P0 Over-scope** → the §10 cut list is non-negotiable; protect it.
- **P0 Reddit gated/rate-limited** → optional from day one; never on the critical path.
- **P1 DataForSEO = single source for the demand signal** → validate data quality on your real catalog in **week 1**, not week 7; budget the $50 early; keep the adapter swappable.
- **P1 Trend↔Seasonality↔keyword shared-source correlation (~55%)** → run the full pairwise redundancy check; prefer the reconciled 3-factor MOS.
- **P2 Cost creep from debugging churn** → realistic total ≈ €250–400 (not €130); cache aggressively; develop on local Ollama.
- **Legal** → Amazon official APIs avoided (documented); DataForSEO/Keepa/eBay used within their redistribution terms (validation data kept internal, not republished).

---

## 13. Verification (how to prove it works end-to-end)
1. **Local stack:** `docker-compose up` → FastAPI `/healthz` 200, Streamlit loads, Postgres reachable.
2. **Golden-path test:** upload a small test catalog (~20 products) with 3–5 images → `POST /catalogs` returns `202 + job_id` → poll `/status` to completion → `/products/{id}/mos` returns a factor breakdown summing to the MOS → `/products/{id}/report` returns a cited recommendation.
3. **Unit tests:** MOS scoring engine (deterministic, fixed-input → fixed-output, including winsorize/min-max edge cases and missing-data handling); each `Connector.fetch()` mocked + one live smoke test.
4. **Vision extraction:** golden set of ~10 labeled images → check extracted attributes + confidence calibration spot-check.
5. **Validation run:** 50–80-product sample → compute Spearman ρ vs Keepa inverse-BSR → assert ρ > 0.35, p < 0.05; produce the figure for the thesis.
6. **IaC:** `terraform validate` + `terraform plan` clean on the target cloud module; (optional) one live `apply` to GKE/Cloud Run.
7. **Cost guardrail:** confirm a full demo run logs to LangSmith/console with cache-hit rate and total token spend within budget.

---

## 14. Recommendations to discuss with your teammate
- Agree the §10 cut list explicitly **before** coding — it's the difference between finishing and not.
- Check whether **your university library** already licenses **Euromonitor Passport or Statista** — if so, that's a free, high-quality Growth-factor upgrade.
- Split ownership along the **infra/API (A)** vs **data/LLM/MOS (B)** seam in the roadmap; the MOS validation and write-up are shared.
- Treat the **MOS validation (Spearman vs Keepa)** and the **proposed→validated factor-set analysis** as your two strongest defensible contributions — invest there over breadth.
