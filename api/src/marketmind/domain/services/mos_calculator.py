"""MosCalculator — the domain service that computes the Market Opportunity Score.

This is the auditable centrepiece of the platform. Given raw per-factor signal
values, it produces a fully transparent :class:`MarketOpportunityScore`.

Algorithm (per factor):
    1. **Impute** missing values. A raw value of ``None`` means "signal
       unavailable". It is replaced by a neutral value placed at the midpoint of
       the factor's reference range and flagged (``imputed=True``) so the report
       can disclose reduced confidence.
    2. **Winsorize / clamp.** Each factor has a reference range ``(min, max)``
       representing (approximately) the 1st/99th percentile of the corpus.
       Because we score a single product at a time, we accept this range as a
       parameter (``corpus_for_normalization``) and clamp the raw value into it,
       which is the winsorization step that tames outliers.
    3. **Min-max normalize** the clamped value to ``[0, 100]``:
           normalized = (clamped - min) / (max - min) * 100
       A degenerate range (``max == min``) normalizes to the neutral midpoint 50.
    4. **Weighted sum.** total = Σ weights[f] * normalized[f].
       Each contribution = weights[f] * normalized[f]; contributions sum to
       total, making the score fully decomposable and explainable.

The service is stateless and pure (no I/O), so it is deterministic and trivially
unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from marketmind.domain.model.scoring import (
    FactorScore,
    MarketOpportunityScore,
    MosFactor,
    MosWeights,
)

# Neutral score used when a signal is missing or its reference range is
# degenerate. Sits at the centre of the [0, 100] band.
NEUTRAL_SCORE: float = 50.0

# Conservative default reference ranges per factor (min, max), interpreted as
# the winsorization bounds. These are sensible defaults for the MVP; in a richer
# system they would be derived from the comparable corpus per factor.
DEFAULT_REFERENCE_RANGES: dict[MosFactor, tuple[float, float]] = {
    MosFactor.TREND: (0.0, 100.0),
    MosFactor.GROWTH: (-10.0, 20.0),
    MosFactor.GEOGRAPHIC: (0.0, 100.0),
    MosFactor.SEASONALITY: (0.0, 100.0),
    MosFactor.CONSUMER: (0.0, 100.0),
}


@dataclass(frozen=True, slots=True)
class MosCalculator:
    """Stateless domain service computing the Market Opportunity Score."""

    def score(
        self,
        raw_signals: Mapping[MosFactor, float | None],
        weights: MosWeights,
        *,
        corpus_for_normalization: Mapping[MosFactor, tuple[float, float]] | None = None,
    ) -> MarketOpportunityScore:
        """Compute the MOS from raw signals.

        Args:
            raw_signals: raw value per factor; ``None`` means missing (imputed).
            weights: the (validated) factor weights.
            corpus_for_normalization: optional per-factor (min, max) reference
                range used for winsorization + min-max normalization. Missing
                factors fall back to :data:`DEFAULT_REFERENCE_RANGES`.

        Returns:
            A :class:`MarketOpportunityScore` whose total equals the sum of its
            contributions (weight x normalized score) across all five factors.
        """
        ranges = dict(DEFAULT_REFERENCE_RANGES)
        if corpus_for_normalization:
            ranges.update(corpus_for_normalization)

        factor_scores: list[FactorScore] = []
        contributions: dict[MosFactor, float] = {}
        total = 0.0

        for factor in MosFactor:
            lo, hi = ranges[factor]
            raw = raw_signals.get(factor)
            imputed = raw is None

            if imputed:
                # Missing signal -> neutral midpoint of the reference range.
                normalized = NEUTRAL_SCORE
                effective_raw = lo + (hi - lo) / 2.0
            else:
                effective_raw = float(raw)  # type: ignore[arg-type]
                # Winsorize: clamp into the reference range.
                clamped = min(max(effective_raw, lo), hi)
                span = hi - lo
                if span <= 0:
                    normalized = NEUTRAL_SCORE
                else:
                    normalized = (clamped - lo) / span * 100.0

            # Guard against tiny floating point excursions outside [0, 100].
            normalized = min(max(normalized, 0.0), 100.0)

            factor_scores.append(
                FactorScore(
                    factor=factor,
                    raw_value=effective_raw,
                    normalized_score=normalized,
                    imputed=imputed,
                )
            )

            contribution = weights[factor] * normalized
            contributions[factor] = contribution
            total += contribution

        total = min(max(total, 0.0), 100.0)

        return MarketOpportunityScore(
            total=total,
            factor_scores=tuple(factor_scores),
            weights=weights,
            contributions=contributions,
        )
