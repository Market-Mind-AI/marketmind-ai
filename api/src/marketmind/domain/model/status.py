"""Analysis lifecycle status."""

from __future__ import annotations

from enum import Enum


class AnalysisStatus(str, Enum):
    """Lifecycle of an :class:`Analysis` aggregate.

    The happy path is:
        PENDING -> EXTRACTING -> ENRICHING -> SCORING
                -> EMBEDDING -> REPORTING -> COMPLETED

    From any non-terminal state the analysis may transition to FAILED.
    """

    PENDING = "pending"
    EXTRACTING = "extracting"
    ENRICHING = "enriching"
    SCORING = "scoring"
    EMBEDDING = "embedding"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED)
