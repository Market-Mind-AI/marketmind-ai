"""SQLAlchemy async ``AnalysisRepository`` with ORM <-> domain mappers.

The mappers are the anti-corruption boundary: the domain ``Analysis`` aggregate
(pure stdlib) never touches SQLAlchemy, and ORM rows never escape this module.
Value objects are (de)serialized to/from JSONB-friendly plain dicts.

This is a stub-grade but functional adapter selected when ``provider_mode`` is
``"real"`` with a Postgres database; the offline default remains
``InMemoryAnalysisRepository``.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketmind.application.ports.ports import AnalysisRepository
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
from marketmind.infrastructure.persistence.sqlalchemy_models import (
    AnalysisModel,
    AnalyzedProductModel,
)


# --------------------------------------------------------------------------- #
# VO -> dict (serialization)                                                   #
# --------------------------------------------------------------------------- #
def _attributes_to_dict(attrs: ProductAttributes) -> dict:
    return {
        "category": attrs.category,
        "subcategory": attrs.subcategory,
        "materials": list(attrs.materials),
        "color": attrs.color,
        "style": attrs.style,
        "key_features": list(attrs.key_features),
        "suggested_keywords": list(attrs.suggested_keywords),
        "confidence": attrs.confidence,
    }


def _enrichment_to_dict(enrichment: Enrichment) -> dict:
    return {
        "raw_signals": {f.value: enrichment.value_for(f) for f in enrichment.raw_signals},
        "sources": list(enrichment.sources),
    }


def _score_to_dict(score: MarketOpportunityScore) -> dict:
    return {
        "total": score.total,
        "factor_scores": [
            {
                "factor": fs.factor.value,
                "raw_value": fs.raw_value,
                "normalized_score": fs.normalized_score,
                "imputed": fs.imputed,
            }
            for fs in score.factor_scores
        ],
        "weights": {f.value: w for f, w in score.weights.weights.items()},
        "contributions": {f.value: c for f, c in score.contributions.items()},
    }


def _market_to_dict(m: MarketRecommendation) -> dict:
    return {
        "country_code": m.country_code,
        "country_name": m.country_name,
        "score": m.score,
        "rationale": m.rationale,
    }


def _embedding_to_dict(emb: ProductEmbedding) -> dict:
    return {
        "vector": list(emb.vector),
        "model": emb.model,
        "version": emb.version,
    }


def _report_to_dict(report: OpportunityReport) -> dict:
    return {
        "verdict": report.verdict,
        "summary": report.summary,
        "markets": [_market_to_dict(m) for m in report.markets],
        "price_band": {
            "low": str(report.price_band.low),
            "high": str(report.price_band.high),
            "currency": report.price_band.currency,
            "note": report.price_band.note,
        },
        "launch_window": {
            "label": report.launch_window.label,
            "peak_note": report.launch_window.peak_note,
        },
        "recommendations": list(report.recommendations),
        "citations": [
            {"source": c.source, "detail": c.detail, "as_of": c.as_of}
            for c in report.citations
        ],
    }


# --------------------------------------------------------------------------- #
# dict -> VO (deserialization)                                                 #
# --------------------------------------------------------------------------- #
def _attributes_from_dict(data: dict | None) -> ProductAttributes | None:
    if data is None:
        return None
    return ProductAttributes(
        category=data["category"],
        subcategory=data["subcategory"],
        materials=tuple(data["materials"]),
        color=data["color"],
        style=data["style"],
        key_features=tuple(data["key_features"]),
        suggested_keywords=tuple(data["suggested_keywords"]),
        confidence=data["confidence"],
    )


def _enrichment_from_dict(data: dict | None) -> Enrichment | None:
    if data is None:
        return None
    raw = {MosFactor(k): v for k, v in data["raw_signals"].items()}
    return Enrichment(raw_signals=raw, sources=tuple(data.get("sources", ())))


def _score_from_dict(data: dict | None) -> MarketOpportunityScore | None:
    if data is None:
        return None
    weights = MosWeights({MosFactor(k): v for k, v in data["weights"].items()})
    factor_scores = tuple(
        FactorScore(
            factor=MosFactor(fs["factor"]),
            raw_value=fs["raw_value"],
            normalized_score=fs["normalized_score"],
            imputed=fs.get("imputed", False),
        )
        for fs in data["factor_scores"]
    )
    contributions = {MosFactor(k): v for k, v in data["contributions"].items()}
    return MarketOpportunityScore(
        total=data["total"],
        factor_scores=factor_scores,
        weights=weights,
        contributions=contributions,
    )


def _market_from_dict(data: dict) -> MarketRecommendation:
    return MarketRecommendation(
        country_code=data["country_code"],
        country_name=data["country_name"],
        score=data["score"],
        rationale=data["rationale"],
    )


def _embedding_from_dict(data: dict | None) -> ProductEmbedding | None:
    if data is None:
        return None
    return ProductEmbedding(
        vector=tuple(data["vector"]),
        model=data["model"],
        version=data["version"],
    )


def _report_from_dict(data: dict | None) -> OpportunityReport | None:
    if data is None:
        return None
    pb = data["price_band"]
    lw = data["launch_window"]
    return OpportunityReport(
        verdict=data["verdict"],
        summary=data["summary"],
        markets=tuple(_market_from_dict(m) for m in data["markets"]),
        price_band=PriceBand(
            low=Decimal(pb["low"]),
            high=Decimal(pb["high"]),
            currency=pb["currency"],
            note=pb.get("note", ""),
        ),
        launch_window=LaunchWindow(label=lw["label"], peak_note=lw["peak_note"]),
        recommendations=tuple(data.get("recommendations", ())),
        citations=tuple(
            Citation(source=c["source"], detail=c["detail"], as_of=c["as_of"])
            for c in data.get("citations", ())
        ),
    )


# --------------------------------------------------------------------------- #
# Aggregate <-> row                                                            #
# --------------------------------------------------------------------------- #
def _to_domain(model: AnalysisModel) -> Analysis:
    return Analysis(
        id=AnalysisId(model.id),
        product_input=ProductInput(
            description=model.description,
            image_refs=tuple(model.image_refs or ()),
        ),
        created_at=model.created_at,
        status=AnalysisStatus(model.status),
        attributes=_attributes_from_dict(model.attributes),
        enrichment=_enrichment_from_dict(model.enrichment),
        score=_score_from_dict(model.score),
        markets=tuple(_market_from_dict(m) for m in (model.markets or ())),
        embedding=_embedding_from_dict(model.embedding),
        report=_report_from_dict(model.report),
        failure_reason=model.failure_reason,
    )


def _apply_to_model(analysis: Analysis, model: AnalysisModel) -> None:
    model.id = analysis.id.value
    model.status = analysis.status.value
    model.created_at = analysis.created_at
    model.description = analysis.product_input.description
    model.image_refs = list(analysis.product_input.image_refs)
    model.attributes = (
        _attributes_to_dict(analysis.attributes) if analysis.attributes else None
    )
    model.enrichment = (
        _enrichment_to_dict(analysis.enrichment) if analysis.enrichment else None
    )
    model.score = _score_to_dict(analysis.score) if analysis.score else None
    model.markets = (
        [_market_to_dict(m) for m in analysis.markets] if analysis.markets else None
    )
    model.embedding = (
        _embedding_to_dict(analysis.embedding) if analysis.embedding else None
    )
    model.report = _report_to_dict(analysis.report) if analysis.report else None
    model.failure_reason = analysis.failure_reason


def _sync_product_projection(analysis: Analysis, model: AnalysisModel) -> None:
    """Keep the ``analyzed_product`` projection in sync with the aggregate.

    Created/updated once an embedding exists. The vector store may also write
    this row directly; here we mirror the aggregate so repository-only callers
    still get a queryable projection.
    """
    if analysis.embedding is None:
        return
    attrs = analysis.attributes
    metadata: dict = {}
    search_parts: list[str] = [analysis.product_input.description]
    if attrs is not None:
        metadata = {
            "category": attrs.category,
            "subcategory": attrs.subcategory,
            "color": attrs.color,
            "style": attrs.style,
            "keywords": list(attrs.suggested_keywords),
        }
        search_parts.extend(
            [attrs.category, attrs.subcategory, *attrs.suggested_keywords]
        )
    product = model.product
    if product is None:
        product = AnalyzedProductModel(analysis_id=analysis.id.value)
        model.product = product
    product.embedding = list(analysis.embedding.vector)
    product.embedding_model = analysis.embedding.model
    product.embedding_version = analysis.embedding.version
    product.mos_score = analysis.score.total if analysis.score else None
    product.product_metadata = metadata
    product.search_text = " ".join(p for p in search_parts if p)


class SqlAlchemyAnalysisRepository(AnalysisRepository):
    """Postgres-backed repository for the ``Analysis`` aggregate."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, analysis: Analysis) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                model = await session.get(AnalysisModel, analysis.id.value)
                if model is None:
                    model = AnalysisModel(id=analysis.id.value)
                    session.add(model)
                _apply_to_model(analysis, model)
                _sync_product_projection(analysis, model)

    async def get(self, analysis_id: AnalysisId) -> Analysis | None:
        async with self._session_factory() as session:
            stmt = select(AnalysisModel).where(
                AnalysisModel.id == _as_uuid(analysis_id)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _to_domain(model)


def _as_uuid(analysis_id: AnalysisId) -> uuid.UUID:
    return analysis_id.value
