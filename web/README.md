# MarketMind AI — Web

The View-Transitions frontend for MarketMind AI. Built with [Astro](https://astro.build)
using native `<ClientRouter />` for app-like page morphing.

## Pipeline UX

1. **`/`** — drag product images + write a description, then `POST /analyses`.
2. **`/analyzing/[id]`** — live SSE progress from `GET /analyses/{id}/events`.
3. **`/report/[id]`** — the rendered Market Opportunity report; the product
   thumbnail/title share a `view-transition-name` so they morph between pages.
4. **`/r/[slug]`** — public, read-only share view of a report.

## Setup

```bash
npm install
npm run dev      # http://localhost:4321
```

Point the app at your FastAPI backend (default `http://localhost:8000`):

```bash
# .env
PUBLIC_API_BASE=http://localhost:8000
```

`PUBLIC_API_BASE` is exposed to the browser (Astro `PUBLIC_` convention) and is
consumed by `src/lib/api.ts`.

## Scripts

| Script            | Action                          |
| ----------------- | ------------------------------- |
| `npm run dev`     | Start the dev server            |
| `npm run build`   | Build static output to `dist/`  |
| `npm run preview` | Preview the production build    |

## Backend contract

The client in `src/lib/api.ts` targets these FastAPI routes:

- `POST /analyses` (multipart: `description` + `images`)
- `GET /analyses/{id}`
- `GET /analyses/{id}/events` (SSE)
- `GET /analyses/{id}/report.pdf`
