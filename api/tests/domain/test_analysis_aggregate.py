"""Lifecycle / state-machine tests for the Analysis aggregate root."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.enrichment import Enrichment
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.model.product import ProductAttributes, ProductInput
from marketmind.domain.model.report import (
    LaunchWindow,
    MarketRecommendation,
    OpportunityReport,
    PriceBand,
)
from marketmind.domain.model.scoring import MosFactor, MosWeights
from marketmind.domain.model.status import AnalysisStatus
from marketmind.domain.services.mos_calculator import MosCalculator
from marketmind.domain.shared.errors import InvalidStateTransition

_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _new_analysis() -> Analysis:
    return Analysis.request(
        analysis_id=AnalysisId(uuid.uuid4()),
        product_input=ProductInput(description="A leather bag", image_refs=()),
        created_at=_NOW,
    )


def _attributes() -> ProductAttributes:
    return ProductAttributes(
        category="accessories",
        subcategory="bags",
        materials=("leather",),
        color="brown",
        style="minimalist",
        key_features=("durable",),
        suggested_keywords=("leather bag",),
        confidence=0.8,
    )


def _enrichment() -> Enrichment:
    return Enrichment(raw_signals={f: 50.0 for f in MosFactor}, sources=("fake",))


def _score():
    return MosCalculator().score({f: 50.0 for f in MosFactor}, MosWeights.default())


def _embedding() -> ProductEmbedding:
    return ProductEmbedding(vector=(0.1, 0.2, 0.3), model="fake", version=1)


def _report() -> OpportunityReport:
    return OpportunityReport(
        verdict="moderate opportunity",
        summary="ok",
        markets=(
            MarketRecommendation(
                country_code="US",
                country_name="United States",
                score=80.0,
                rationale="big",
            ),
        ),
        price_band=PriceBand(low=Decimal("10"), high=Decimal("20"), currency="USD"),
        launch_window=LaunchWindow(label="Q4", peak_note="holidays"),
    )


def _advance_to(target: AnalysisStatus) -> Analysis:
    """Drive a fresh analysis up to (but not into) the given target state."""
    a = _new_analysis()
    if target == AnalysisStatus.PENDING:
        return a
    a.start_extraction()
    if target == AnalysisStatus.EXTRACTING:
        return a
    a.record_attributes(_attributes())
    if target == AnalysisStatus.ENRICHING:
        return a
    a.record_signals(_enrichment())
    if target == AnalysisStatus.SCORING:
        return a
    a.record_score(_score())
    if target == AnalysisStatus.EMBEDDING:
        return a
    a.record_embedding(_embedding())
    if target == AnalysisStatus.REPORTING:
        return a
    a.record_report(_report())
    return a  # COMPLETED


# --- happy path -------------------------------------------------------------
def test_full_happy_path_reaches_completed() -> None:
    a = _new_analysis()
    assert a.status is AnalysisStatus.PENDING

    a.start_extraction()
    assert a.status is AnalysisStatus.EXTRACTING

    a.record_attributes(_attributes())
    assert a.status is AnalysisStatus.ENRICHING
    assert a.attributes is not None

    a.record_signals(_enrichment())
    assert a.status is AnalysisStatus.SCORING

    a.record_score(_score())
    assert a.status is AnalysisStatus.EMBEDDING
    assert a.score is not None

    a.record_embedding(_embedding())
    assert a.status is AnalysisStatus.REPORTING

    a.record_report(_report())
    assert a.status is AnalysisStatus.COMPLETED
    assert a.is_complete is True
    # report markets backfilled when none recorded explicitly.
    assert a.markets


def test_record_markets_during_reporting() -> None:
    a = _advance_to(AnalysisStatus.REPORTING)
    markets = (
        MarketRecommendation(
            country_code="DE",
            country_name="Germany",
            score=70.0,
            rationale="demand",
        ),
    )
    a.record_markets(markets)
    assert a.markets == markets
    assert a.status is AnalysisStatus.REPORTING  # no transition


# --- illegal transitions ----------------------------------------------------
def test_cannot_record_attributes_before_extraction() -> None:
    a = _new_analysis()  # PENDING
    with pytest.raises(InvalidStateTransition):
        a.record_attributes(_attributes())


def test_cannot_skip_extraction_to_scoring() -> None:
    a = _new_analysis()
    a.start_extraction()  # EXTRACTING
    with pytest.raises(InvalidStateTransition):
        a.record_score(_score())


def test_cannot_start_extraction_twice() -> None:
    a = _new_analysis()
    a.start_extraction()
    with pytest.raises(InvalidStateTransition):
        a.start_extraction()


def test_cannot_record_signals_from_pending() -> None:
    a = _new_analysis()
    with pytest.raises(InvalidStateTransition):
        a.record_signals(_enrichment())


def test_cannot_record_report_before_reporting() -> None:
    a = _advance_to(AnalysisStatus.EMBEDDING)
    with pytest.raises(InvalidStateTransition):
        a.record_report(_report())


def test_cannot_record_markets_outside_reporting() -> None:
    a = _advance_to(AnalysisStatus.SCORING)
    with pytest.raises(InvalidStateTransition):
        a.record_markets(())


# --- failure handling -------------------------------------------------------
@pytest.mark.parametrize(
    "state",
    [
        AnalysisStatus.PENDING,
        AnalysisStatus.EXTRACTING,
        AnalysisStatus.ENRICHING,
        AnalysisStatus.SCORING,
        AnalysisStatus.EMBEDDING,
        AnalysisStatus.REPORTING,
    ],
)
def test_fail_allowed_from_any_non_terminal_state(state: AnalysisStatus) -> None:
    a = _advance_to(state)
    a.fail("boom")
    assert a.status is AnalysisStatus.FAILED
    assert a.failure_reason == "boom"


def test_fail_blocked_from_completed() -> None:
    a = _advance_to(AnalysisStatus.COMPLETED)
    with pytest.raises(InvalidStateTransition):
        a.fail("too late")


def test_no_transition_out_of_failed() -> None:
    a = _new_analysis()
    a.fail("boom")
    with pytest.raises(InvalidStateTransition):
        a.start_extraction()


# --- identity ---------------------------------------------------------------
def test_identity_equality_by_id_not_value() -> None:
    aid = AnalysisId(uuid.uuid4())
    a1 = Analysis.request(aid, ProductInput("x"), _NOW)
    a2 = Analysis.request(aid, ProductInput("y"), _NOW)
    a2.start_extraction()  # different state, same identity
    assert a1 == a2
    assert hash(a1) == hash(a2)
