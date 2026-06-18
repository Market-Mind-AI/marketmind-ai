"""Enrichment signals value object.

Holds the raw per-factor signal values gathered from public data providers
(trends, macro/geographic, marketplace). A value of ``None`` means the signal
was unavailable and must be imputed by the MosCalculator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from marketmind.domain.model.scoring import MosFactor
from marketmind.domain.shared.errors import InvalidValueObject
from marketmind.domain.shared.value_object import ImmutableValue


@dataclass(frozen=True, slots=True)
class Enrichment(ImmutableValue):
    """Raw, un-normalized market signals keyed by :class:`MosFactor`."""

    raw_signals: Mapping[MosFactor, float | None]
    sources: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for factor in self.raw_signals:
            if not isinstance(factor, MosFactor):
                raise InvalidValueObject(
                    f"Enrichment.raw_signals key {factor!r} is not a MosFactor"
                )
        object.__setattr__(
            self, "raw_signals", MappingProxyType(dict(self.raw_signals))
        )

    def value_for(self, factor: MosFactor) -> float | None:
        return self.raw_signals.get(factor)
