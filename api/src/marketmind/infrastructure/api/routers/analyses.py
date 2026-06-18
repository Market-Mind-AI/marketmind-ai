"""Analyses router — the primary inbound HTTP surface.

Endpoints:
  * ``POST /analyses``               multipart (description + images[]) -> 201
  * ``GET  /analyses/{id}``          fetch the projected analysis view
  * ``GET  /analyses/{id}/stream``   SSE live pipeline progress
  * ``GET  /analyses/{id}/report.pdf`` rendered report bytes
  * ``GET  /r/{slug}``               public shareable view (slug == id hex)

Every handler goes through an application use case — repositories and adapters
are never touched directly. The slug is the analysis UUID hex, so it round-trips
back to an :class:`AnalysisId` without extra persistence.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from marketmind.application.dto import AnalyzeProductCommand
from marketmind.application.errors import AnalysisNotFound
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.shared.errors import InvalidValueObject
from marketmind.infrastructure.api.deps import (
    get_analyze_use_case,
    get_container,
    get_get_use_case,
)
from marketmind.infrastructure.api.schemas import AnalysisResponse, AnalyzeResponse
from marketmind.infrastructure.api.sse import analysis_event_stream
from marketmind.infrastructure.config.di import Container

router = APIRouter(tags=["analyses"])


def _slug_for(analysis_id: AnalysisId) -> str:
    return analysis_id.value.hex


def _analysis_id_from_slug(slug: str) -> AnalysisId:
    try:
        return AnalysisId(uuid.UUID(hex=slug))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Unknown share link") from exc


def _parse_id(raw: str) -> AnalysisId:
    try:
        return AnalysisId.from_string(raw)
    except InvalidValueObject as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/analyses",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(
    description: str = Form(...),
    images: list[UploadFile] = File(default=[]),
    use_case=Depends(get_analyze_use_case),
):
    uploaded = []
    for image in images:
        data = await image.read()
        uploaded.append(
            (
                image.filename or "upload.bin",
                data,
                image.content_type or "application/octet-stream",
            )
        )

    command = AnalyzeProductCommand(description=description, images=uploaded)
    analysis_id = await use_case.handle(command)

    return AnalyzeResponse(
        analysis_id=str(analysis_id),
        slug=_slug_for(analysis_id),
        status="completed",
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    use_case=Depends(get_get_use_case),
):
    aid = _parse_id(analysis_id)
    try:
        view = await use_case.handle(aid)
    except AnalysisNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AnalysisResponse.from_view(view)


@router.get("/analyses/{analysis_id}/stream")
async def stream_analysis(
    analysis_id: str,
    container: Container = Depends(get_container),
):
    aid = _parse_id(analysis_id)
    return analysis_event_stream(container.progress_publisher, aid)


@router.get("/analyses/{analysis_id}/report.pdf")
async def analysis_report_pdf(
    analysis_id: str,
    container: Container = Depends(get_container),
):
    aid = _parse_id(analysis_id)
    analysis = await container.repository.get(aid)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {aid}")
    if analysis.report is None:
        raise HTTPException(status_code=409, detail="Report not ready for this analysis")
    pdf_bytes = await container.pdf_renderer.render(analysis.report, analysis)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report-{aid.value.hex}.pdf"'},
    )


@router.get("/r/{slug}", response_model=AnalysisResponse)
async def shared_analysis(
    slug: str,
    use_case=Depends(get_get_use_case),
):
    aid = _analysis_id_from_slug(slug)
    try:
        view = await use_case.handle(aid)
    except AnalysisNotFound as exc:
        raise HTTPException(status_code=404, detail="Unknown share link") from exc
    return AnalysisResponse.from_view(view)
