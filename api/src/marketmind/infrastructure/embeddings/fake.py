"""Offline deterministic embedding model.

Produces a stable unit-norm vector derived from a hash of the product's
description + attributes, so identical products embed identically (and similar
text lands nearby under cosine). Lets the vector-store / comparables path run
fully offline. Real embeddings use :class:`CohereEmbeddingModel`.
"""

from __future__ import annotations

import hashlib
import math
import struct

from marketmind.application.ports.ports import EmbeddingModel
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.product import ProductAttributes


def _deterministic_vector(seed_text: str, dimensions: int) -> tuple[float, ...]:
    """A stable, unit-norm float vector of length ``dimensions`` from text.

    Expands a BLAKE2b digest into ``dimensions`` floats in [-1, 1], then
    L2-normalizes so cosine similarity is well-behaved.
    """
    raw = bytearray()
    counter = 0
    needed = dimensions * 4  # 4 bytes per float32
    while len(raw) < needed:
        digest = hashlib.blake2b(
            seed_text.encode("utf-8"),
            digest_size=64,
            salt=struct.pack("<I", counter % (1 << 32)).ljust(16, b"\x00")[:16],
        ).digest()
        raw.extend(digest)
        counter += 1

    values: list[float] = []
    for i in range(dimensions):
        chunk = bytes(raw[i * 4 : i * 4 + 4])
        # Map a uint32 to [-1, 1].
        (uint,) = struct.unpack("<I", chunk)
        values.append((uint / float(1 << 31)) - 1.0)

    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return tuple(v / norm for v in values)


class FakeEmbeddingModel(EmbeddingModel):
    """Deterministic, dependency-free embedding model for offline use."""

    def __init__(
        self,
        *,
        dimensions: int = 1024,
        model: str = "fake-embed",
        version: int = 1,
    ) -> None:
        self._dimensions = dimensions
        self._model = model
        self._version = version

    async def embed(
        self,
        description: str,
        attributes: ProductAttributes,
        image_refs: list[str],
    ) -> ProductEmbedding:
        seed = "␟".join(
            (
                description.strip().lower(),
                attributes.category,
                attributes.subcategory,
                attributes.color,
                attributes.style,
                "|".join(attributes.materials),
                "|".join(attributes.key_features),
                "|".join(attributes.suggested_keywords),
            )
        )
        return ProductEmbedding(
            vector=_deterministic_vector(seed, self._dimensions),
            model=self._model,
            version=self._version,
        )
