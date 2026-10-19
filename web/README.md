# MarketMind AI — Web

The Astro 5 frontend for MarketMind AI, static output with `<ClientRouter />`
view transitions. Every number comes from the backend; the browser never scores.

## Pages

| Route | What it does |
| --- | --- |
| `/` | Upload a photo and/or describe the product, pick the target markets, review the identified fields, start the analysis. The request goes to the pending-analyses dock and the user stays on the page. |
| `/report/[id]` | The report for one analysis request id: live loader while the pipeline runs, then the MOS ranking, grouped per-dimension scores and the narrative, with a sticky action bar (copy share link). |
| `/r/[slug]` | Read-only share view of the same report; the slug is the request UUID hex. |
| `/404` | Not found. |

`[id]` and `[slug]` are resolved **client-side** (each `getStaticPaths` emits a single
`_` placeholder, see `nginx/default.conf` at the repo root). There is no `/analyzing`
page, no `/analyses` API and no PDF export.

## Layout

- `src/layouts/Base.astro` — document shell, fonts, language toggle, `<ClientRouter />`.
- `src/components/RequestsDock.astro` — the pending-analyses dock: reads `mm:requests`
  from `localStorage`, subscribes to each running request's SSE stream, toasts when
  one finishes.
- `src/components/ReportView.astro` — the report body mounted by both `/report/[id]`
  and `/r/[slug]`.
- `src/lib/api.ts` — typed client (endpoints below), country catalog cache, MOS tier
  colors, slug helpers, `localStorage` request store.
- `src/lib/i18n.ts` — EN/ES, 100 keys each, `t()` + `applyTranslations()`; the
  choice lives in `localStorage` under `mm:lang` (falls back to `navigator.language`).
- `src/lib/grouped-scores.ts` — renders a country's deterministic scores grouped by
  dimension as nested progress bars.

## Setup

```bash
npm install
cp .env.example .env   # PUBLIC_API_BASE=http://localhost:8081
npm run dev            # http://localhost:4321
```

`PUBLIC_API_BASE` is exposed to the browser (Astro `PUBLIC_` convention) and
**inlined at build time**. In dev it points at the orchestrator (`8081`); pointing it
at the scoring service (`8004`) works too but bypasses the agent. The Docker image
bakes `/api`.

## Scripts

| Script | Action |
| --- | --- |
| `npm run dev` | Start the dev server |
| `npm run build` | Build static output to `dist/` |
| `npm run preview` | Preview the production build |

From the repo root, `make help` / `make install` / `make dev` / `make build` /
`make preview` wrap the same commands.

`tests/e2e.spec.ts` is a Playwright smoke test (`playwright.config.ts`); Playwright
is not a project dependency, install it separately to run it.

## Endpoints consumed (`src/lib/api.ts`)

- `GET /countries` — available markets, ordered by continent then name; cached once per page.
- `POST /catalog/identify-image` — `{ image_base64, image_media_type, hint_text, countries }`;
  image or text, at least one.
- `POST /analyze` — confirmed fields + `countries` → `202 { request_id, status }`.
- `GET /analyze/{id}/stream` — SSE with `{ status, progress, has_explanation, narrative_abandoned }`
  on every change; held open past `done` until the narrative lands.
- `GET /analyze/{id}` — full payload (`result`, `explanation`, `breakdown`); polled as
  fallback every 2.5 s without a stream, 15 s with one, up to 6 min.
