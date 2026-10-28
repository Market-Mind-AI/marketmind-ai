import { defineConfig } from "astro/config";

// MarketMind AI frontend. View transitions are enabled per-page via the
// <ClientRouter /> component included in the Base layout.
export default defineConfig({
  // Static output: dynamic [id]/[slug] routes are resolved client-side from the
  // URL path (see each page's getStaticPaths fallback + the client scripts),
  // so no server runtime is required.
  output: "static",
  server: {
    port: 4321,
    host: true,
  },
  // `npm run dev` serves the pages on :4321 and the orchestrator answers on
  // :8081 with no CORS, so the browser cannot call it directly. The dev server
  // forwards /api to it instead — the same thing nginx does in the deployed
  // image — and the bundle keeps PUBLIC_API_BASE=/api in both.
  vite: {
    server: {
      proxy: {
        "/api": {
          target: process.env.API_PROXY_TARGET ?? "http://localhost:8081",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  },
});
