"""AnalyzeProductUseCase — orchestrates the full analysis pipeline.

This is plain async Python (no framework, no LangGraph). The pipeline is:

    extract attributes
      -> store images
      -> fan-out enrichment (asyncio.gather over MarketSignalProvider list)
      -> score (MosCalculator, a pure domain service)
      -> embed + vector-store upsert
      -> geo-rank target markets
      -> generate report (with comparables retrieved from the vector store)
      -> persist

Progress is published at every step through the ProgressPublisher port so the
inbound SSE adapter can stream live status. On any failure the analysis is marked
FAILED, persisted, and an :class:`AnalysisPipelineError` is raised.

NOTE (intentional future work): an OPTIONAL infrastructure orchestrator could
re-express this exact flow as a LangGraph state machine without changing the
domain or these ports. It is deliberately NOT implemented here to keep the use
case framework-agnostic and stdlib-only.
"""

from __future__ import annotations

import asyncio

from marketmind.application.dto import AnalyzeProductCommand
from marketmind.application.errors import AnalysisPipelineError
from marketmind.application.ports.ports import (
    AnalysisRepository,
    Clock,
    EmbeddingModel,
    GeoMarketRanker,
    IdGenerator,
    MarketSignalProvider,
    ObjectStorage,
    ProductAttributeExtractor,
    ProgressPublisher,
    ReportGenerator,
    VectorStore,
)
from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.enrichment import Enrichment
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.model.product import ProductAttributes, ProductInput
from marketmind.domain.model.scoring import MosFactor, MosWeights
from marketmind.domain.services.mos_calculator import MosCalculator

# Number of comparable products to retrieve for report grounding.
_COMPARABLES_K = 5


class AnalyzeProductUseCase:
    """Command handler that runs the end-to-end product analysis pipeline."""

    def __init__(
        self,
        *,
        repository: AnalysisRepository,
        object_storage: ObjectStorage,
        extractor: ProductAttributeExtractor,
        signal_providers: list[MarketSignalProvider],
        mos_calculator: MosCalculator,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        geo_ranker: GeoMarketRanker,
        report_generator: ReportGenerator,
        progress: ProgressPublisher,
        clock: Clock,
        id_generator: IdGenerator,
        weights: MosWeights | None = None,
    ) -> None:
        self._repository = repository
        self._storage = object_storage
        self._extractor = extractor
        self._signal_providers = signal_providers
        self._calculator = mos_calculator
        self._embedding_model = embedding_model
        self._vector_store = vector_store
        self._geo_ranker = geo_ranker
        self._report_generator = report_generator
        self._progress = progress
        self._clock = clock
        self._ids = id_generator
        self._weights = weights or MosWeights.default()

    async def handle(self, command: AnalyzeProductCommand) -> AnalysisId:
        """Run the pipeline; returns the new AnalysisId. Persists at each step."""
        # 1. Store images first so we have stable refs for the aggregate.
        image_refs = await self._store_images(command)

        analysis = Analysis.request(
            analysis_id=self._ids.new_analysis_id(),
            product_input=ProductInput(
                description=command.description,
                image_refs=tuple(image_refs),
            ),
            created_at=self._clock.now(),
        )
        await self._repository.save(analysis)

        step = "start"
        try:
            # 2. Extract attributes.
            step = "extracting"
            analysis.start_extraction()
            await self._publish(analysis.id, step, "Extracting product attributes")
            attributes = await self._extractor.extract(command.description, list(image_refs))
            analysis.record_attributes(attributes)
            await self._repository.save(analysis)

            # 3. Fan-out enrichment across all signal providers concurrently.
            step = "enriching"
            await self._publish(analysis.id, step, "Gathering market signals")
            raw_signals = await self._gather_signals(attributes)
            enrichment = Enrichment(
                raw_signals=raw_signals,
                sources=tuple(p.factor.value for p in self._signal_providers),
            )
            analysis.record_signals(enrichment)
            await self._repository.save(analysis)

            # 4. Score (pure domain service).
            step = "scoring"
            await self._publish(analysis.id, step, "Computing opportunity score")
            score = self._calculator.score(raw_signals, self._weights)
            analysis.record_score(score)
            await self._repository.save(analysis)

            # 5. Embed + upsert into the vector store.
            step = "embedding"
            await self._publish(analysis.id, step, "Embedding & indexing product")
            embedding = await self._embedding_model.embed(
                command.description, attributes, list(image_refs)
            )
            await self._vector_store.upsert(
                analysis.id,
                embedding,
                metadata={
                    "category": attributes.category,
                    "subcategory": attributes.subcategory,
                    "mos_total": score.total,
                },
            )
            analysis.record_embedding(embedding)
            await self._repository.save(analysis)

            # 6. Reporting: rank markets, retrieve comparables, generate report.
            step = "reporting"
            await self._publish(analysis.id, step, "Ranking markets & writing report")
            markets = await self._geo_ranker.rank(attributes, raw_signals)
            analysis.record_markets(tuple(markets))

            comparables = await self._vector_store.query_comparables(
                embedding,
                k=_COMPARABLES_K,
                filters={"category": attributes.category},
            )
            report = await self._report_generator.generate(analysis, comparables)
            analysis.record_report(report)
            await self._repository.save(analysis)

            await self._publish(analysis.id, "completed", "Analysis complete")
            return analysis.id

        except Exception as exc:
            analysis.fail(f"{step}: {exc}")
            await self._repository.save(analysis)
            await self._publish(analysis.id, "failed", str(exc))
            raise AnalysisPipelineError(str(analysis.id), step, str(exc)) from exc

    # ----- helpers ------------------------------------------------------
    async def _store_images(self, command: AnalyzeProductCommand) -> list[str]:
        refs: list[str] = []
        for filename, data, content_type in command.images:
            ref = await self._storage.store(filename, data, content_type)
            refs.append(ref)
        return refs

    async def _gather_signals(self, attributes: ProductAttributes) -> dict[MosFactor, float | None]:
        """Fan out over providers; a provider failure imputes None for its factor."""

        async def _one(provider: MarketSignalProvider) -> tuple[MosFactor, float | None]:
            try:
                value = await provider.fetch(attributes)
                return provider.factor, value
            except Exception:
                return provider.factor, None

        results = await asyncio.gather(*(_one(p) for p in self._signal_providers))
        signals: dict[MosFactor, float | None] = {f: None for f in MosFactor}
        for factor, value in results:
            signals[factor] = value
        return signals

    async def _publish(self, analysis_id: AnalysisId, step: str, detail: str) -> None:
        await self._progress.publish(analysis_id, step, detail)
