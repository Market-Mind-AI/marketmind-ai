# MarketMind AI frontend — Astro static build served by nginx.
#
# There is no server runtime here on purpose: astro.config.mjs sets
# output: "static", and the dynamic [id]/[slug] routes are resolved in the
# browser (see nginx/default.conf for how those are routed).

FROM node:22-alpine AS build

WORKDIR /app/web

# Astro inlines PUBLIC_* variables into the JS bundle at BUILD time — a static
# build has nothing left running to read an env var later. Changing the API
# base therefore requires rebuilding the image, which is why this is an ARG and
# not a container env var. Setting it as a Deployment env var would do nothing.
#
# Default "/api": the web app and marketmind-core are published on the same
# host (marketmind-dev.<region>.cloudapp.azure.com) and routed by path, so a
# relative base keeps every call same-origin. That means no CORS preflight, and
# no hostname baked into the bundle — the same image works on any hostname.
ARG PUBLIC_API_BASE=/api

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./

# Written as .env.production rather than exported into the shell because Vite
# resolves .env.[mode] with higher priority than .env, so this wins even if a
# stray .env slips into the build context.
RUN printf 'PUBLIC_API_BASE=%s\n' "$PUBLIC_API_BASE" > .env.production && \
    npm run build


FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/web/dist /usr/share/nginx/html

EXPOSE 8080
