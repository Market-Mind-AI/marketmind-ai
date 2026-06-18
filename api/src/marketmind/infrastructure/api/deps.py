"""FastAPI dependency providers sourced from the composition root.

Controllers never construct adapters or use cases directly; they receive them
through these dependencies, which pull the process-wide :class:`Container`
stored on ``app.state`` during the lifespan.
"""

from __future__ import annotations

from fastapi import Request

from marketmind.application.use_cases.analyze_product import AnalyzeProductUseCase
from marketmind.application.use_cases.get_analysis import GetAnalysisUseCase
from marketmind.infrastructure.config.di import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_analyze_use_case(request: Request) -> AnalyzeProductUseCase:
    container: Container = request.app.state.container
    return container.build_analyze_use_case()


def get_get_use_case(request: Request) -> GetAnalysisUseCase:
    container: Container = request.app.state.container
    return container.build_get_use_case()
