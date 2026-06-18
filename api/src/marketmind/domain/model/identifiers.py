"""Strongly-typed identifiers for domain aggregates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from marketmind.domain.shared.errors import InvalidValueObject


@dataclass(frozen=True, slots=True)
class AnalysisId:
    """Identity of the :class:`Analysis` aggregate root."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidValueObject("AnalysisId must wrap a uuid.UUID")

    @staticmethod
    def new() -> "AnalysisId":
        return AnalysisId(uuid.uuid4())

    @staticmethod
    def from_string(raw: str) -> "AnalysisId":
        try:
            return AnalysisId(uuid.UUID(raw))
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidValueObject(f"Invalid AnalysisId: {raw!r}") from exc

    def __str__(self) -> str:
        return str(self.value)
