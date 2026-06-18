"""Product-related value objects: the submitted input and extracted attributes."""

from __future__ import annotations

from dataclasses import dataclass, field

from marketmind.domain.shared.errors import InvalidValueObject


@dataclass(frozen=True, slots=True)
class ProductInput:
    """The raw submission from the user: a free-text description and image refs.

    ``image_refs`` are opaque storage references/URLs (the application layer
    stores the uploaded bytes via the ObjectStorage port and keeps the refs).
    """

    description: str
    image_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.description or not self.description.strip():
            raise InvalidValueObject("ProductInput.description must be non-empty")
        if not isinstance(self.image_refs, tuple):
            raise InvalidValueObject("ProductInput.image_refs must be a tuple")


@dataclass(frozen=True, slots=True)
class ProductAttributes:
    """Structured attributes extracted from the product images + description.

    Produced by a vision LLM (via the ProductAttributeExtractor port).
    ``confidence`` is the model's self-reported confidence in [0, 1].
    """

    category: str
    subcategory: str
    materials: tuple[str, ...]
    color: str
    style: str
    key_features: tuple[str, ...]
    suggested_keywords: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        if not self.category or not self.category.strip():
            raise InvalidValueObject("ProductAttributes.category must be non-empty")
        for name in ("materials", "key_features", "suggested_keywords"):
            if not isinstance(getattr(self, name), tuple):
                raise InvalidValueObject(f"ProductAttributes.{name} must be a tuple")
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidValueObject(
                "ProductAttributes.confidence must be in [0, 1], " f"got {self.confidence!r}"
            )
