"""Deterministic unit tests for the MosCalculator domain service.

Reference ranges (DEFAULT_REFERENCE_RANGES):
    TREND      (0, 100)
    GROWTH     (-10, 20)
    GEOGRAPHIC (0, 100)
    SEASONALITY(0, 100)
    CONSUMER   (0, 100)

Default weights: TREND 0.30, GROWTH 0.25, GEOGRAPHIC 0.20,
                 SEASONALITY 0.15, CONSUMER 0.10.
"""

from __future__ import annotations

import math

import pytest

from marketmind.domain.model.scoring import MosFactor, MosWeights
from marketmind.domain.services.mos_calculator import (
    DEFAULT_REFERENCE_RANGES,
    NEUTRAL_SCORE,
    MosCalculator,
)
from marketmind.domain.shared.errors import InvalidWeights

CALC = MosCalculator()
TOL = 1e-6


def _normalized(score, factor: MosFactor) -> float:
    for fs in score.factor_scores:
        if fs.factor is factor:
            return fs.normalized_score
    raise AssertionError(f"missing factor {factor}")


def test_min_max_normalization_per_factor() -> None:
    raw = {
        MosFactor.TREND: 80.0,  # (0,100)  -> 80
        MosFactor.GROWTH: 5.0,  # (-10,20) -> (5+10)/30*100 = 50
        MosFactor.GEOGRAPHIC: 60.0,  # -> 60
        MosFactor.SEASONALITY: 70.0,  # -> 70
        MosFactor.CONSUMER: 50.0,  # -> 50
    }
    score = CALC.score(raw, MosWeights.default())

    assert _normalized(score, MosFactor.TREND) == pytest.approx(80.0)
    assert _normalized(score, MosFactor.GROWTH) == pytest.approx(50.0)
    assert _normalized(score, MosFactor.GEOGRAPHIC) == pytest.approx(60.0)
    assert _normalized(score, MosFactor.SEASONALITY) == pytest.approx(70.0)
    assert _normalized(score, MosFactor.CONSUMER) == pytest.approx(50.0)


def test_weighted_sum_total() -> None:
    raw = {
        MosFactor.TREND: 80.0,
        MosFactor.GROWTH: 5.0,
        MosFactor.GEOGRAPHIC: 60.0,
        MosFactor.SEASONALITY: 70.0,
        MosFactor.CONSUMER: 50.0,
    }
    score = CALC.score(raw, MosWeights.default())
    # 0.30*80 + 0.25*50 + 0.20*60 + 0.15*70 + 0.10*50
    # = 24 + 12.5 + 12 + 10.5 + 5 = 64.0
    assert score.total == pytest.approx(64.0)


def test_contributions_sum_to_total() -> None:
    raw = {
        MosFactor.TREND: 30.0,
        MosFactor.GROWTH: 0.0,
        MosFactor.GEOGRAPHIC: 90.0,
        MosFactor.SEASONALITY: 20.0,
        MosFactor.CONSUMER: 100.0,
    }
    score = CALC.score(raw, MosWeights.default())
    assert sum(score.contributions.values()) == pytest.approx(score.total, abs=TOL)
    # each contribution == weight * normalized
    for fs in score.factor_scores:
        expected = score.weights[fs.factor] * fs.normalized_score
        assert score.contributions[fs.factor] == pytest.approx(expected, abs=TOL)


def test_winsorize_clamps_above_and_below_range() -> None:
    raw = {
        MosFactor.TREND: 250.0,  # clamp to 100 -> 100
        MosFactor.GROWTH: -50.0,  # clamp to -10 -> 0
        MosFactor.GEOGRAPHIC: 50.0,
        MosFactor.SEASONALITY: 50.0,
        MosFactor.CONSUMER: 50.0,
    }
    score = CALC.score(raw, MosWeights.default())
    assert _normalized(score, MosFactor.TREND) == pytest.approx(100.0)
    assert _normalized(score, MosFactor.GROWTH) == pytest.approx(0.0)


def test_custom_corpus_range_overrides_default() -> None:
    # Provide a tighter TREND range; value 50 in (0,200) -> 25.
    raw = {f: 50.0 for f in MosFactor}
    score = CALC.score(
        raw,
        MosWeights.default(),
        corpus_for_normalization={MosFactor.TREND: (0.0, 200.0)},
    )
    assert _normalized(score, MosFactor.TREND) == pytest.approx(25.0)


def test_degenerate_range_yields_neutral() -> None:
    raw = {f: 50.0 for f in MosFactor}
    score = CALC.score(
        raw,
        MosWeights.default(),
        corpus_for_normalization={MosFactor.TREND: (10.0, 10.0)},
    )
    assert _normalized(score, MosFactor.TREND) == pytest.approx(NEUTRAL_SCORE)


def test_missing_value_imputed_to_neutral_and_flagged() -> None:
    raw: dict[MosFactor, float | None] = {f: 50.0 for f in MosFactor}
    raw[MosFactor.CONSUMER] = None
    score = CALC.score(raw, MosWeights.default())

    consumer = next(fs for fs in score.factor_scores if fs.factor is MosFactor.CONSUMER)
    assert consumer.imputed is True
    assert consumer.normalized_score == pytest.approx(NEUTRAL_SCORE)
    # imputed raw_value sits at the midpoint of the reference range.
    lo, hi = DEFAULT_REFERENCE_RANGES[MosFactor.CONSUMER]
    assert consumer.raw_value == pytest.approx(lo + (hi - lo) / 2.0)
    # non-missing factors are not flagged.
    for fs in score.factor_scores:
        if fs.factor is not MosFactor.CONSUMER:
            assert fs.imputed is False


def test_all_missing_yields_neutral_total() -> None:
    raw = {f: None for f in MosFactor}
    score = CALC.score(raw, MosWeights.default())
    assert score.total == pytest.approx(NEUTRAL_SCORE)
    assert all(fs.imputed for fs in score.factor_scores)


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(InvalidWeights):
        MosWeights(
            {
                MosFactor.TREND: 0.5,
                MosFactor.GROWTH: 0.5,
                MosFactor.GEOGRAPHIC: 0.5,
                MosFactor.SEASONALITY: 0.5,
                MosFactor.CONSUMER: 0.5,
            }
        )


def test_weights_negative_rejected() -> None:
    with pytest.raises(InvalidWeights):
        MosWeights(
            {
                MosFactor.TREND: -0.1,
                MosFactor.GROWTH: 0.35,
                MosFactor.GEOGRAPHIC: 0.25,
                MosFactor.SEASONALITY: 0.30,
                MosFactor.CONSUMER: 0.20,
            }
        )


def test_default_weights_sum_to_one() -> None:
    w = MosWeights.default()
    assert math.isclose(sum(w.weights.values()), 1.0, abs_tol=TOL)


def test_normalized_is_idempotent_for_valid_weights() -> None:
    # The constructor requires weights to already sum to 1.0, so normalize()
    # is a no-op rescale that still sums to 1.0.
    w = MosWeights({f: 0.2 for f in MosFactor}).normalized()
    assert math.isclose(sum(w.weights.values()), 1.0, abs_tol=TOL)
    for f in MosFactor:
        assert w[f] == pytest.approx(0.2)


@pytest.mark.parametrize(
    "trend_value, expected_tier",
    [
        (100.0, "strong"),  # total dominated high -> >=70
        (50.0, "moderate"),
        (0.0, "weak"),
    ],
)
def test_tier_thresholds(trend_value: float, expected_tier: str) -> None:
    # Build a score whose total lands in each band by varying one big-weight factor.
    raw = {
        MosFactor.TREND: trend_value,
        MosFactor.GROWTH: 20.0
        if expected_tier == "strong"
        else (5.0 if expected_tier == "moderate" else -10.0),
        MosFactor.GEOGRAPHIC: 100.0
        if expected_tier == "strong"
        else (50.0 if expected_tier == "moderate" else 0.0),
        MosFactor.SEASONALITY: 100.0
        if expected_tier == "strong"
        else (50.0 if expected_tier == "moderate" else 0.0),
        MosFactor.CONSUMER: 100.0
        if expected_tier == "strong"
        else (50.0 if expected_tier == "moderate" else 0.0),
    }
    score = CALC.score(raw, MosWeights.default())
    assert score.tier == expected_tier


def test_tier_boundary_exact_values() -> None:
    # total exactly 70 -> strong; exactly 45 -> moderate; just below -> weak.
    # Use uniform normalized value v so total == v (weights sum to 1).
    def total_for(v: float):
        # pick raw producing normalized v on a (0,100) range factor set
        raw = {f: v for f in MosFactor}
        # GROWTH range is (-10,20); map desired normalized v back to raw.
        raw[MosFactor.GROWTH] = -10.0 + v / 100.0 * 30.0
        return CALC.score(raw, MosWeights.default())

    assert total_for(70.0).tier == "strong"
    assert total_for(45.0).tier == "moderate"
    assert total_for(44.9).tier == "weak"
