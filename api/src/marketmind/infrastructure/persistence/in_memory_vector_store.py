"""Pure-Python (numpy-free) in-memory ``VectorStore`` — the offline default.

Computes cosine similarity in plain Python over stored embeddings. Supports the
same ``category`` / ``region`` metadata filtering semantics as the pgvector
adapter so the two are behaviourally interchangeable for the use case.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from marketmind.application.ports.ports import VectorStore
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.identifiers import AnalysisId


@dataclass
class _Record:
    analysis_id: str
    vector: tuple[float, ...]
    model: str
    version: int
    metadata: dict


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Cosine similarity in [-1, 1]; 0.0 for a degenerate (zero) vector."""
    if len(a) != len(b):
        # Different dimensionality -> not comparable.
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _matches(metadata: dict, filters: dict) -> bool:
    """A record matches when every provided filter key equals its value.

    Recognised filter keys mirror the pgvector adapter: ``category`` and
    ``region``. Unknown keys are matched generically against metadata too.
    """
    for key, expected in filters.items():
        if expected is None:
            continue
        if metadata.get(key) != expected:
            return False
    return True


class InMemoryVectorStore(VectorStore):
    """Process-local cosine vector store for tests and offline runs."""

    def __init__(self) -> None:
        self._records: dict[str, _Record] = {}

    async def upsert(
        self,
        analysis_id: AnalysisId,
        embedding: ProductEmbedding,
        metadata: dict,
    ) -> None:
        key = str(analysis_id)
        self._records[key] = _Record(
            analysis_id=key,
            vector=tuple(embedding.vector),
            model=embedding.model,
            version=embedding.version,
            metadata=dict(metadata),
        )

    async def query_comparables(
        self,
        embedding: ProductEmbedding,
        *,
        k: int,
        filters: dict,
    ) -> list[dict]:
        query = tuple(embedding.vector)
        scored: list[tuple[float, _Record]] = []
        for record in self._records.values():
            if not _matches(record.metadata, filters):
                continue
            similarity = _cosine(query, record.vector)
            scored.append((similarity, record))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        results: list[dict] = []
        for similarity, record in scored[: max(k, 0)]:
            results.append(
                {
                    "analysis_id": record.analysis_id,
                    "similarity": similarity,
                    "distance": 1.0 - similarity,
                    "model": record.model,
                    "version": record.version,
                    "metadata": dict(record.metadata),
                }
            )
        return results
