"""Shared kernel for the domain layer (errors, identifiers)."""

from marketmind.domain.shared.errors import (
    DomainError,
    InvalidStateTransition,
    InvalidValueObject,
    InvalidWeights,
    MissingPrerequisite,
)

__all__ = [
    "DomainError",
    "InvalidStateTransition",
    "InvalidValueObject",
    "InvalidWeights",
    "MissingPrerequisite",
]
