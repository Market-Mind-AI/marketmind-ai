"""Domain events (past tense) for the Market Opportunity Analysis context.

Plain frozen dataclasses. They are not (yet) dispatched through a bus — the use
case emits progress through the ProgressPublisher port — but they are defined so
an outbox/event-bus infrastructure adapter can adopt them later without touching
the domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marketmind.domain.model.identifiers import AnalysisId


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for domain events."""

    analysis_id: AnalysisId
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisRequested(DomainEvent):
    """A new analysis was requested by a user."""

    description: str
    image_count: int


@dataclass(frozen=True, slots=True)
class AttributesExtracted(DomainEvent):
    """Product attributes were extracted by the vision model."""

    category: str
    confidence: float


@dataclass(frozen=True, slots=True)
class AnalysisScored(DomainEvent):
    """The Market Opportunity Score was computed."""

    total: float
    tier: str


@dataclass(frozen=True, slots=True)
class AnalysisCompleted(DomainEvent):
    """The analysis finished successfully and a report is available."""

    verdict: str


@dataclass(frozen=True, slots=True)
class AnalysisFailed(DomainEvent):
    """The analysis failed."""

    reason: str
