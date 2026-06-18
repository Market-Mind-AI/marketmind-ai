"""Outbound ports (driven side of the hexagon).

These are ``typing.Protocol`` interfaces the application layer depends on.
Infrastructure adapters implement them. They are framework-free and reference
only domain types (and stdlib). Async where the operation does I/O.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.model.product import ProductAttributes
from marketmind.domain.model.report import MarketRecommendation, OpportunityReport
from marketmind.domain.model.scoring import MosFactor


@runtime_checkable
class AnalysisRepository(Protocol):
    """Persistence port for the Analysis aggregate (one repo per aggregate)."""

    async def save(self, analysis: Analysis) -> None: ...

    async def get(self, analysis_id: AnalysisId) -> Analysis | None: ...


@runtime_checkable
class ObjectStorage(Protocol):
    """Blob storage for uploaded product images. Returns an opaque ref/url."""

    async def store(self, filename: str, data: bytes, content_type: str) -> str: ...

    async def load(self, ref: str) -> bytes: ...


@runtime_checkable
class ProductAttributeExtractor(Protocol):
    """Vision-LLM extraction of structured attributes from images + text."""

    async def extract(self, description: str, image_refs: list[str]) -> ProductAttributes: ...


@runtime_checkable
class MarketSignalProvider(Protocol):
    """One enrichment source contributing the raw value for a single factor.

    The use case is given a ``list[MarketSignalProvider]`` and fans out over
    them concurrently. ``factor`` declares which MOS factor this provider feeds.
    """

    @property
    def factor(self) -> MosFactor: ...

    async def fetch(self, attributes: ProductAttributes) -> float: ...


@runtime_checkable
class GeoMarketRanker(Protocol):
    """Ranks candidate target markets (countries) for a product."""

    async def rank(
        self,
        attributes: ProductAttributes,
        signals: dict[MosFactor, float | None],
    ) -> list[MarketRecommendation]: ...


@runtime_checkable
class EmbeddingModel(Protocol):
    """Produces a dense embedding for a product (for comparable retrieval)."""

    async def embed(
        self,
        description: str,
        attributes: ProductAttributes,
        image_refs: list[str],
    ) -> ProductEmbedding: ...


@runtime_checkable
class VectorStore(Protocol):
    """Stores product embeddings and retrieves comparable products."""

    async def upsert(
        self,
        analysis_id: AnalysisId,
        embedding: ProductEmbedding,
        metadata: dict[str, object],
    ) -> None: ...

    async def query_comparables(
        self,
        embedding: ProductEmbedding,
        *,
        k: int,
        filters: dict[str, object],
    ) -> list[dict[str, object]]: ...


@runtime_checkable
class ReportGenerator(Protocol):
    """Generates the explainable OpportunityReport (report-generation LLM)."""

    async def generate(
        self, analysis: Analysis, comparables: list[dict[str, object]]
    ) -> OpportunityReport: ...


@runtime_checkable
class PdfRenderer(Protocol):
    """Renders an OpportunityReport to PDF bytes."""

    async def render(self, report: OpportunityReport, analysis: Analysis) -> bytes: ...


@runtime_checkable
class ProgressPublisher(Protocol):
    """Publishes pipeline progress and exposes an SSE subscription stream."""

    async def publish(self, analysis_id: AnalysisId, step: str, detail: str) -> None: ...

    def subscribe(self, analysis_id: AnalysisId) -> AsyncIterator[dict[str, object]]: ...


@runtime_checkable
class Clock(Protocol):
    """Supplies the current time (injected for determinism/testability)."""

    def now(self) -> datetime: ...


@runtime_checkable
class IdGenerator(Protocol):
    """Generates new aggregate identities."""

    def new_analysis_id(self) -> AnalysisId: ...
