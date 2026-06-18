"""Application DTOs: input commands and output views.

Views are deliberately decoupled from the domain model so inbound adapters
(FastAPI) never serialize domain entities directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.scoring import MosFactor

# An uploaded image as received by the inbound adapter.
UploadedImage = tuple[str, bytes, str]  # (filename, data, content_type)


@dataclass(frozen=True, slots=True)
class AnalyzeProductCommand:
    """Command to run the full analysis pipeline for one product."""

    description: str
    images: list[UploadedImage] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FactorContributionView:
    factor: str
    weight: float
    normalized_score: float
    contribution: float
    imputed: bool


@dataclass(frozen=True, slots=True)
class ScoreView:
    total: float
    tier: str
    explanation: str
    contributions: tuple[FactorContributionView, ...]


@dataclass(frozen=True, slots=True)
class MarketView:
    country_code: str
    country_name: str
    score: float
    rationale: str


@dataclass(frozen=True, slots=True)
class CitationView:
    source: str
    detail: str
    as_of: str


@dataclass(frozen=True, slots=True)
class ReportView:
    verdict: str
    summary: str
    markets: tuple[MarketView, ...]
    price_low: str
    price_high: str
    currency: str
    price_note: str
    launch_label: str
    launch_peak_note: str
    recommendations: tuple[str, ...]
    citations: tuple[CitationView, ...]


@dataclass(frozen=True, slots=True)
class AnalysisView:
    """Output projection of an Analysis aggregate for inbound adapters."""

    id: str
    status: str
    created_at: datetime
    description: str
    image_refs: tuple[str, ...]
    category: str | None
    score: ScoreView | None
    report: ReportView | None
    failure_reason: str | None

    @staticmethod
    def from_domain(analysis: Analysis) -> AnalysisView:
        """Map a domain Analysis into a flat, serializable view."""
        score_view: ScoreView | None = None
        if analysis.score is not None:
            s = analysis.score
            contribs = tuple(
                FactorContributionView(
                    factor=fs.factor.value,
                    weight=s.weights[fs.factor],
                    normalized_score=fs.normalized_score,
                    contribution=s.contributions.get(fs.factor, 0.0),
                    imputed=fs.imputed,
                )
                for fs in s.factor_scores
            )
            score_view = ScoreView(
                total=s.total,
                tier=s.tier,
                explanation=s.explanation(),
                contributions=contribs,
            )

        report_view: ReportView | None = None
        if analysis.report is not None:
            r = analysis.report
            report_view = ReportView(
                verdict=r.verdict,
                summary=r.summary,
                markets=tuple(
                    MarketView(
                        country_code=m.country_code,
                        country_name=m.country_name,
                        score=m.score,
                        rationale=m.rationale,
                    )
                    for m in r.markets
                ),
                price_low=str(r.price_band.low),
                price_high=str(r.price_band.high),
                currency=r.price_band.currency,
                price_note=r.price_band.note,
                launch_label=r.launch_window.label,
                launch_peak_note=r.launch_window.peak_note,
                recommendations=r.recommendations,
                citations=tuple(
                    CitationView(source=c.source, detail=c.detail, as_of=c.as_of)
                    for c in r.citations
                ),
            )

        return AnalysisView(
            id=str(analysis.id),
            status=analysis.status.value,
            created_at=analysis.created_at,
            description=analysis.product_input.description,
            image_refs=analysis.product_input.image_refs,
            category=analysis.attributes.category if analysis.attributes else None,
            score=score_view,
            report=report_view,
            failure_reason=analysis.failure_reason,
        )


__all__ = [
    "AnalysisView",
    "AnalyzeProductCommand",
    "CitationView",
    "FactorContributionView",
    "MarketView",
    "MosFactor",
    "ReportView",
    "ScoreView",
    "UploadedImage",
]
