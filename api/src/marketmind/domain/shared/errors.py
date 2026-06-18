"""Domain-layer errors.

These are raised by the pure business logic when an invariant is violated.
They depend on the Python standard library only.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-rule violations."""


class InvalidStateTransition(DomainError):
    """Raised when an Analysis is moved through an illegal lifecycle transition."""

    def __init__(self, current: str, attempted: str) -> None:
        self.current = current
        self.attempted = attempted
        super().__init__(f"Illegal status transition: {current!r} -> {attempted!r}")


class InvalidWeights(DomainError):
    """Raised when MosWeights do not sum to 1.0 or contain invalid values."""


class InvalidValueObject(DomainError):
    """Raised when a value object fails its construction-time validation."""


class MissingPrerequisite(DomainError):
    """Raised when a behaviour needs prior state that has not been recorded yet."""
