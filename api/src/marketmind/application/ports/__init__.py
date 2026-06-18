"""Outbound ports for the application layer (typing.Protocol interfaces)."""

from marketmind.application.ports.ports import (
    AnalysisRepository,
    Clock,
    EmbeddingModel,
    GeoMarketRanker,
    IdGenerator,
    MarketSignalProvider,
    ObjectStorage,
    PdfRenderer,
    ProductAttributeExtractor,
    ProgressPublisher,
    ReportGenerator,
    VectorStore,
)

__all__ = [
    "AnalysisRepository",
    "ObjectStorage",
    "ProductAttributeExtractor",
    "MarketSignalProvider",
    "GeoMarketRanker",
    "EmbeddingModel",
    "VectorStore",
    "ReportGenerator",
    "PdfRenderer",
    "ProgressPublisher",
    "Clock",
    "IdGenerator",
]
