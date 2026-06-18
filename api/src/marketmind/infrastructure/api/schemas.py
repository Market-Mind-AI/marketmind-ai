"""HTTP response schemas (pydantic v2).

These are the serialization boundary of the inbound adapter. They are built
exclusively from application Views (``AnalysisView`` & friends) — never from
domain entities, so the domain model never leaks over the wire.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from marketmind.application.dto import AnalysisView, ReportView, ScoreView


class HealthResponse(BaseModel):
    status: str = "ok"
    provider_mode: str


class AnalyzeResponse(BaseModel):
    """Returned by ``POST /analyses`` (201)."""

    analysis_id: str
    slug: str
    status: str


class FactorContributionResponse(BaseModel):
    factor: str
    weight: float
    normalized_score: float
    contribution: float
    imputed: bool


class ScoreResponse(BaseModel):
    total: float
    tier: str
    explanation: str
    contributions: list[FactorContributionResponse]

    @classmethod
    def from_view(cls, view: ScoreView) -> ScoreResponse:
        return cls(
            total=view.total,
            tier=view.tier,
            explanation=view.explanation,
            contributions=[
                FactorContributionResponse(
                    factor=c.factor,
                    weight=c.weight,
                    normalized_score=c.normalized_score,
                    contribution=c.contribution,
                    imputed=c.imputed,
                )
                for c in view.contributions
            ],
        )


class MarketResponse(BaseModel):
    country_code: str
    country_name: str
    score: float
    rationale: str


class CitationResponse(BaseModel):
    source: str
    detail: str
    as_of: str


class ReportResponse(BaseModel):
    verdict: str
    summary: str
    markets: list[MarketResponse]
    price_low: str
    price_high: str
    currency: str
    price_note: str
    launch_label: str
    launch_peak_note: str
    recommendations: list[str]
    citations: list[CitationResponse]

    @classmethod
    def from_view(cls, view: ReportView) -> ReportResponse:
        return cls(
            verdict=view.verdict,
            summary=view.summary,
            markets=[
                MarketResponse(
                    country_code=m.country_code,
                    country_name=m.country_name,
                    score=m.score,
                    rationale=m.rationale,
                )
                for m in view.markets
            ],
            price_low=view.price_low,
            price_high=view.price_high,
            currency=view.currency,
            price_note=view.price_note,
            launch_label=view.launch_label,
            launch_peak_note=view.launch_peak_note,
            recommendations=list(view.recommendations),
            citations=[
                CitationResponse(source=c.source, detail=c.detail, as_of=c.as_of)
                for c in view.citations
            ],
        )


class AnalysisResponse(BaseModel):
    """Returned by ``GET /analyses/{id}`` and the public ``GET /r/{slug}``."""

    id: str
    status: str
    created_at: datetime
    description: str
    image_refs: list[str]
    category: str | None
    score: ScoreResponse | None
    report: ReportResponse | None
    failure_reason: str | None

    @classmethod
    def from_view(cls, view: AnalysisView) -> AnalysisResponse:
        return cls(
            id=view.id,
            status=view.status,
            created_at=view.created_at,
            description=view.description,
            image_refs=list(view.image_refs),
            category=view.category,
            score=ScoreResponse.from_view(view.score) if view.score else None,
            report=ReportResponse.from_view(view.report) if view.report else None,
            failure_reason=view.failure_reason,
        )


__all__ = [
    "AnalysisResponse",
    "AnalyzeResponse",
    "CitationResponse",
    "FactorContributionResponse",
    "HealthResponse",
    "MarketResponse",
    "ReportResponse",
    "ScoreResponse",
]
