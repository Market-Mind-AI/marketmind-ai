"""Liveness/readiness router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from marketmind.infrastructure.api.deps import get_container
from marketmind.infrastructure.api.schemas import HealthResponse
from marketmind.infrastructure.config.di import Container

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz(container: Container = Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        provider_mode=container.settings.provider_mode,
    )
