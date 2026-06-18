"""Product embedding value object (for vector similarity / comparables)."""

from __future__ import annotations

from dataclasses import dataclass

from marketmind.domain.shared.errors import InvalidValueObject


@dataclass(frozen=True, slots=True)
class ProductEmbedding:
    """A dense vector representation of a product, plus model provenance."""

    vector: tuple[float, ...]
    model: str
    version: int

    def __post_init__(self) -> None:
        if not isinstance(self.vector, tuple) or not self.vector:
            raise InvalidValueObject("ProductEmbedding.vector must be a non-empty tuple")
        if not self.model or not self.model.strip():
            raise InvalidValueObject("ProductEmbedding.model must be non-empty")
        if self.version < 1:
            raise InvalidValueObject("ProductEmbedding.version must be >= 1")

    @property
    def dimensions(self) -> int:
        return len(self.vector)
