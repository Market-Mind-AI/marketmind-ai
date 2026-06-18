"""Market Opportunity Score (MOS) value objects.

The MOS is the auditable centrepiece of the product. It is a weighted sum of
five normalized factor scores. Every value object here is frozen and validates
its own invariants so the score is always internally consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from marketmind.domain.shared.errors import InvalidValueObject, InvalidWeights
from marketmind.domain.shared.value_object import ImmutableValue

# Tolerance for floating-point weight-sum / contribution comparisons.
_EPSILON = 1e-6


class MosFactor(str, Enum):
    """The five factors that compose the Market Opportunity Score."""

    TREND = "trend"
    GROWTH = "growth"
    GEOGRAPHIC = "geographic"
    SEASONALITY = "seasonality"
    CONSUMER = "consumer"


# Default weighting (must sum to 1.0).
_DEFAULT_WEIGHTS: dict[MosFactor, float] = {
    MosFactor.TREND: 0.30,
    MosFactor.GROWTH: 0.25,
    MosFactor.GEOGRAPHIC: 0.20,
    MosFactor.SEASONALITY: 0.15,
    MosFactor.CONSUMER: 0.10,
}


@dataclass(frozen=True, slots=True)
class MosWeights(ImmutableValue):
    """Per-factor weights for the weighted MOS sum.

    Must define a weight for every :class:`MosFactor`, all non-negative, summing
    to 1.0. Use :meth:`default` for the spec's default weighting and
    :meth:`normalized` to rescale arbitrary positive weights so they sum to 1.0.
    """

    weights: Mapping[MosFactor, float]

    def __post_init__(self) -> None:
        missing = set(MosFactor) - set(self.weights)
        if missing:
            raise InvalidWeights(
                f"MosWeights missing factors: {sorted(f.value for f in missing)}"
            )
        for factor, w in self.weights.items():
            if not isinstance(factor, MosFactor):
                raise InvalidWeights(f"Weight key {factor!r} is not a MosFactor")
            if w < 0:
                raise InvalidWeights(f"Weight for {factor.value} is negative: {w}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > _EPSILON:
            raise InvalidWeights(
                f"MosWeights must sum to 1.0, got {total!r}"
            )
        # Freeze the mapping so the value object is truly immutable.
        object.__setattr__(
            self, "weights", MappingProxyType(dict(self.weights))
        )

    @staticmethod
    def default() -> "MosWeights":
        return MosWeights(dict(_DEFAULT_WEIGHTS))

    def normalized(self) -> "MosWeights":
        """Return weights rescaled to sum exactly to 1.0."""
        total = sum(self.weights.values())
        if total <= 0:
            raise InvalidWeights("Cannot normalize weights that sum to <= 0")
        return MosWeights({f: w / total for f, w in self.weights.items()})

    def __getitem__(self, factor: MosFactor) -> float:
        return self.weights[factor]


@dataclass(frozen=True, slots=True)
class FactorScore:
    """A single factor's raw value and its min-max normalized score in [0, 100].

    ``imputed`` flags that the raw value was missing (None) and substituted with
    a neutral midpoint, so the report can disclose reduced confidence.
    """

    factor: MosFactor
    raw_value: float
    normalized_score: float
    imputed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.factor, MosFactor):
            raise InvalidValueObject("FactorScore.factor must be a MosFactor")
        if not 0.0 <= self.normalized_score <= 100.0:
            raise InvalidValueObject(
                "FactorScore.normalized_score must be in [0, 100], "
                f"got {self.normalized_score!r}"
            )


@dataclass(frozen=True, slots=True)
class MarketOpportunityScore(ImmutableValue):
    """The composite, auditable Market Opportunity Score.

    ``total`` in [0, 100] is the weighted sum of the factor scores.
    ``contributions[factor] = weights[factor] * factor.normalized_score`` and the
    contributions sum (approximately) to ``total`` — making the score fully
    transparent.
    """

    total: float
    factor_scores: tuple[FactorScore, ...]
    weights: MosWeights
    contributions: Mapping[MosFactor, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.total <= 100.0:
            raise InvalidValueObject(
                f"MarketOpportunityScore.total must be in [0, 100], got {self.total!r}"
            )
        if not self.factor_scores:
            raise InvalidValueObject("MarketOpportunityScore requires factor_scores")
        object.__setattr__(
            self, "contributions", MappingProxyType(dict(self.contributions))
        )

    @property
    def tier(self) -> str:
        """Coarse verdict band derived from the total score."""
        if self.total >= 70.0:
            return "strong"
        if self.total >= 45.0:
            return "moderate"
        return "weak"

    def explanation(self) -> str:
        """Human-readable, ordered breakdown of how the total was formed."""
        lines = [
            f"Market Opportunity Score: {self.total:.1f}/100 ({self.tier}).",
            "Contributions (weight x normalized score):",
        ]
        ordered = sorted(
            self.factor_scores,
            key=lambda fs: self.contributions.get(fs.factor, 0.0),
            reverse=True,
        )
        for fs in ordered:
            w = self.weights[fs.factor]
            contrib = self.contributions.get(fs.factor, 0.0)
            flag = " (imputed)" if fs.imputed else ""
            lines.append(
                f"  - {fs.factor.value}: {w:.2f} x {fs.normalized_score:.1f}"
                f" = {contrib:.1f}{flag}"
            )
        return "\n".join(lines)
