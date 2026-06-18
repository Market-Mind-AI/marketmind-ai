"""Application-layer errors (use-case orchestration failures)."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for application/use-case errors."""


class AnalysisNotFound(ApplicationError):
    """Raised when a requested analysis does not exist."""

    def __init__(self, analysis_id: str) -> None:
        self.analysis_id = analysis_id
        super().__init__(f"Analysis not found: {analysis_id}")


class AnalysisPipelineError(ApplicationError):
    """Raised when the analysis pipeline fails during orchestration."""

    def __init__(self, analysis_id: str, step: str, cause: str) -> None:
        self.analysis_id = analysis_id
        self.step = step
        self.cause = cause
        super().__init__(
            f"Analysis {analysis_id} failed at step {step!r}: {cause}"
        )
