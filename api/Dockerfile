# syntax=docker/dockerfile:1
# =============================================================================
# MarketMind AI — API container
# python:3.12-slim + uv. Default CMD runs the offline (all-fakes) FastAPI app.
# =============================================================================
FROM python:3.12-slim AS base

# uv: fast, reproducible dependency installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# --- Dependency layer (cached unless lock/pyproject changes) ------------------
COPY pyproject.toml uv.lock* README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --frozen 2>/dev/null \
    || uv sync --no-install-project --no-dev

# --- Application layer --------------------------------------------------------
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# --- Runtime ------------------------------------------------------------------
ENV MARKETMIND_HOST=0.0.0.0 \
    MARKETMIND_PORT=8000
EXPOSE 8000

# Non-root for safety.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.data/uploads \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "marketmind.main:app", "--host", "0.0.0.0", "--port", "8000"]
