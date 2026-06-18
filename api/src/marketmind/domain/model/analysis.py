"""The Analysis aggregate root.

This is the single aggregate of the "Market Opportunity Analysis" bounded
context. It owns the full lifecycle of one product analysis and enforces the
state machine PENDING -> EXTRACTING -> ENRICHING -> SCORING -> EMBEDDING ->
REPORTING -> COMPLETED (or FAILED from any non-terminal state). Behaviour lives
on the entity (rich model), not in services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.enrichment import Enrichment
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.model.product import ProductAttributes, ProductInput
from marketmind.domain.model.report import MarketRecommendation, OpportunityReport
from marketmind.domain.model.scoring import MarketOpportunityScore
from marketmind.domain.model.status import AnalysisStatus
from marketmind.domain.shared.errors import (
    InvalidStateTransition,
    MissingPrerequisite,
)

# Allowed forward transitions of the lifecycle state machine.
_ALLOWED: dict[AnalysisStatus, frozenset[AnalysisStatus]] = {
    AnalysisStatus.PENDING: frozenset({AnalysisStatus.EXTRACTING}),
    AnalysisStatus.EXTRACTING: frozenset({AnalysisStatus.ENRICHING}),
    AnalysisStatus.ENRICHING: frozenset({AnalysisStatus.SCORING}),
    AnalysisStatus.SCORING: frozenset({AnalysisStatus.EMBEDDING}),
    AnalysisStatus.EMBEDDING: frozenset({AnalysisStatus.REPORTING}),
    AnalysisStatus.REPORTING: frozenset({AnalysisStatus.COMPLETED}),
    AnalysisStatus.COMPLETED: frozenset(),
    AnalysisStatus.FAILED: frozenset(),
}


@dataclass(eq=False)
class Analysis:
    """Aggregate root for a single product market-opportunity analysis."""

    id: AnalysisId
    product_input: ProductInput
    created_at: datetime
    status: AnalysisStatus = AnalysisStatus.PENDING
    attributes: ProductAttributes | None = None
    enrichment: Enrichment | None = None
    score: MarketOpportunityScore | None = None
    markets: tuple[MarketRecommendation, ...] = field(default_factory=tuple)
    embedding: ProductEmbedding | None = None
    report: OpportunityReport | None = None
    failure_reason: str | None = None

    # ----- construction -------------------------------------------------
    @staticmethod
    def request(
        analysis_id: AnalysisId,
        product_input: ProductInput,
        created_at: datetime,
    ) -> "Analysis":
        """Factory for a freshly requested (PENDING) analysis."""
        return Analysis(
            id=analysis_id,
            product_input=product_input,
            created_at=created_at,
            status=AnalysisStatus.PENDING,
        )

    # ----- state machine ------------------------------------------------
    def _transition_to(self, target: AnalysisStatus) -> None:
        if target not in _ALLOWED.get(self.status, frozenset()):
            raise InvalidStateTransition(self.status.value, target.value)
        self.status = target

    # ----- behaviour (each step records its output and advances state) --
    def start_extraction(self) -> None:
        """PENDING -> EXTRACTING."""
        self._transition_to(AnalysisStatus.EXTRACTING)

    def record_attributes(self, attributes: ProductAttributes) -> None:
        """Store extracted attributes; EXTRACTING -> ENRICHING."""
        if self.status is not AnalysisStatus.EXTRACTING:
            raise InvalidStateTransition(self.status.value, "record_attributes")
        self.attributes = attributes
        self._transition_to(AnalysisStatus.ENRICHING)

    def record_signals(self, enrichment: Enrichment) -> None:
        """Store enrichment signals; ENRICHING -> SCORING."""
        if self.status is not AnalysisStatus.ENRICHING:
            raise InvalidStateTransition(self.status.value, "record_signals")
        if self.attributes is None:
            raise MissingPrerequisite("Cannot record signals before attributes")
        self.enrichment = enrichment
        self._transition_to(AnalysisStatus.SCORING)

    def record_score(self, score: MarketOpportunityScore) -> None:
        """Store the MOS; SCORING -> EMBEDDING."""
        if self.status is not AnalysisStatus.SCORING:
            raise InvalidStateTransition(self.status.value, "record_score")
        self.score = score
        self._transition_to(AnalysisStatus.EMBEDDING)

    def record_embedding(self, embedding: ProductEmbedding) -> None:
        """Store the product embedding; EMBEDDING -> REPORTING."""
        if self.status is not AnalysisStatus.EMBEDDING:
            raise InvalidStateTransition(self.status.value, "record_embedding")
        self.embedding = embedding
        self._transition_to(AnalysisStatus.REPORTING)

    def record_markets(self, markets: tuple[MarketRecommendation, ...]) -> None:
        """Store ranked target markets. Allowed during REPORTING (no transition)."""
        if self.status is not AnalysisStatus.REPORTING:
            raise InvalidStateTransition(self.status.value, "record_markets")
        self.markets = tuple(markets)

    def record_report(self, report: OpportunityReport) -> None:
        """Store the final report; REPORTING -> COMPLETED."""
        if self.status is not AnalysisStatus.REPORTING:
            raise InvalidStateTransition(self.status.value, "record_report")
        self.report = report
        if not self.markets:
            self.markets = report.markets
        self._transition_to(AnalysisStatus.COMPLETED)

    def fail(self, reason: str) -> None:
        """Mark the analysis FAILED from any non-terminal state."""
        if self.status.is_terminal:
            raise InvalidStateTransition(self.status.value, AnalysisStatus.FAILED.value)
        self.failure_reason = reason
        self.status = AnalysisStatus.FAILED

    # ----- queries ------------------------------------------------------
    @property
    def is_complete(self) -> bool:
        return self.status is AnalysisStatus.COMPLETED

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Analysis) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)
