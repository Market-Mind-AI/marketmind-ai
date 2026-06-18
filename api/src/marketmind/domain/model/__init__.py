"""Domain model: the Analysis aggregate and its value objects."""

from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.enrichment import Enrichment
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.model.product import ProductAttributes, ProductInput
from marketmind.domain.model.report import (
    Citation,
    LaunchWindow,
    MarketRecommendation,
    OpportunityReport,
    PriceBand,
)
from marketmind.domain.model.scoring import (
    FactorScore,
    MarketOpportunityScore,
    MosFactor,
    MosWeights,
)
from marketmind.domain.model.status import AnalysisStatus

__all__ = [
    "Analysis",
    "AnalysisId",
    "AnalysisStatus",
    "ProductInput",
    "ProductAttributes",
    "Enrichment",
    "MosFactor",
    "MosWeights",
    "FactorScore",
    "MarketOpportunityScore",
    "MarketRecommendation",
    "PriceBand",
    "LaunchWindow",
    "Citation",
    "OpportunityReport",
    "ProductEmbedding",
]
