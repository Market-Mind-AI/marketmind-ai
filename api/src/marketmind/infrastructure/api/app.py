"""FastAPI application factory.

``create_app`` builds the composition root, stores it on ``app.state`` for the
process lifetime via the lifespan, mounts the routers, configures CORS for the
Astro dev frontend, and maps domain/application errors to HTTP responses.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from marketmind.application.errors import (
    AnalysisNotFound,
    AnalysisPipelineError,
    ApplicationError,
)
from marketmind.domain.shared.errors import (
    DomainError,
    InvalidStateTransition,
    InvalidValueObject,
)
from marketmind.infrastructure.api.routers import analyses, health
from marketmind.infrastructure.config.di import Container, build_container
from marketmind.infrastructure.config.settings import Settings, get_settings

# Default CORS allow-list for local Astro dev plus the configured origins.
_ASTRO_DEV_ORIGINS = [
    "http://localhost:4321",
    "http://127.0.0.1:4321",
]


def create_app(
    container: Container | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    """Build and return a fully-wired FastAPI app (offline-ready by default)."""
    resolved_settings = settings or (container.settings if container else get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or build_container(resolved_settings)
        try:
            yield
        finally:
            await app.state.container.aclose()

    app = FastAPI(
        title="MarketMind AI",
        version="0.1.0",
        summary="Generative-AI commercial-intelligence platform",
        lifespan=lifespan,
    )

    _configure_cors(app, resolved_settings)
    _register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(analyses.router)

    return app


def _configure_cors(app: FastAPI, settings: Settings) -> None:
    origins = list(dict.fromkeys([*_ASTRO_DEV_ORIGINS, *settings.cors_origins]))
    allow_all = "*" in settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AnalysisNotFound)
    async def _not_found(request: Request, exc: AnalysisNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidValueObject)
    async def _invalid_vo(request: Request, exc: InvalidValueObject) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(InvalidStateTransition)
    async def _bad_transition(
        request: Request, exc: InvalidStateTransition
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(AnalysisPipelineError)
    async def _pipeline_error(
        request: Request, exc: AnalysisPipelineError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
                "step": exc.step,
                "analysis_id": exc.analysis_id,
            },
        )

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ApplicationError)
    async def _app_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})


__all__ = ["create_app"]
