"""Report value objects: recommendations, pricing, timing, citations, report."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from marketmind.domain.shared.errors import InvalidValueObject


@dataclass(frozen=True, slots=True)
class MarketRecommendation:
    """A ranked target market (country) with a 0..100 attractiveness score."""

    country_code: str
    country_name: str
    score: float
    rationale: str

    def __post_init__(self) -> None:
        if not self.country_code or len(self.country_code) not in (2, 3):
            raise InvalidValueObject("MarketRecommendation.country_code must be an ISO-2/3 code")
        if not 0.0 <= self.score <= 100.0:
            raise InvalidValueObject(
                "MarketRecommendation.score must be in [0, 100], " f"got {self.score!r}"
            )


@dataclass(frozen=True, slots=True)
class PriceBand:
    """Suggested retail price band in a given currency."""

    low: Decimal
    high: Decimal
    currency: str
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.low, Decimal) or not isinstance(self.high, Decimal):
            raise InvalidValueObject("PriceBand.low/high must be Decimal")
        if self.low < 0 or self.high < 0:
            raise InvalidValueObject("PriceBand prices must be non-negative")
        if self.high < self.low:
            raise InvalidValueObject("PriceBand.high must be >= low")
        if not self.currency or len(self.currency) != 3:
            raise InvalidValueObject("PriceBand.currency must be an ISO-4217 code")


@dataclass(frozen=True, slots=True)
class LaunchWindow:
    """Suggested go-to-market timing."""

    label: str
    peak_note: str

    def __post_init__(self) -> None:
        if not self.label or not self.label.strip():
            raise InvalidValueObject("LaunchWindow.label must be non-empty")


@dataclass(frozen=True, slots=True)
class Citation:
    """A traceable source backing a claim in the report."""

    source: str
    detail: str
    as_of: str

    def __post_init__(self) -> None:
        if not self.source or not self.source.strip():
            raise InvalidValueObject("Citation.source must be non-empty")


@dataclass(frozen=True, slots=True)
class OpportunityReport:
    """The explainable final deliverable for an analysis."""

    verdict: str
    summary: str
    markets: tuple[MarketRecommendation, ...]
    price_band: PriceBand
    launch_window: LaunchWindow
    recommendations: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[Citation, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.verdict or not self.verdict.strip():
            raise InvalidValueObject("OpportunityReport.verdict must be non-empty")
        for name in ("markets", "recommendations", "citations"):
            if not isinstance(getattr(self, name), tuple):
                raise InvalidValueObject(f"OpportunityReport.{name} must be a tuple")
