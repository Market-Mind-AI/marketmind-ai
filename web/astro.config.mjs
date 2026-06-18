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
});
