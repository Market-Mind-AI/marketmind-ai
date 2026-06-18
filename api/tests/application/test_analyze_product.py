"""End-to-end test of AnalyzeProductUseCase with all fake adapters (offline)."""

from __future__ import annotations

import pytest

from marketmind.application.dto import AnalysisView, AnalyzeProductCommand
from marketmind.application.errors import AnalysisNotFound, AnalysisPipelineError
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.model.scoring import MosFactor
from marketmind.domain.model.status import AnalysisStatus

_EXPECTED_STEPS = [
    "extracting",
    "enriching",
    "scoring",
    "embedding",
    "reporting",
    "completed",
]


async def test_pipeline_completes_with_score_and_report(
    analyze_use_case, repository, progress
) -> None:
    command = AnalyzeProductCommand(description="A handmade leather backpack", images=[])

    analysis_id = await analyze_use_case.handle(command)
    assert isinstance(analysis_id, AnalysisId)

    analysis = await repository.get(analysis_id)
    assert analysis is not None
    assert analysis.status is AnalysisStatus.COMPLETED
    assert analysis.is_complete is True

    # Score present and well-formed.
    assert analysis.score is not None
    assert 0.0 <= analysis.score.total <= 100.0
    assert analysis.score.tier in {"strong", "moderate", "weak"}
    assert len(analysis.score.factor_scores) == len(list(MosFactor))

    # Report present and grounded.
    assert analysis.report is not None
    assert analysis.report.verdict
    assert analysis.markets  # markets recorded
    assert analysis.embedding is not None
    assert analysis.attributes is not None


async def test_progress_published_for_every_step(analyze_use_case, progress) -> None:
    await analyze_use_case.handle(AnalyzeProductCommand(description="A ceramic mug", images=[]))
    steps = [e["step"] for e in progress.events]
    assert steps == _EXPECTED_STEPS


async def test_uploaded_images_become_refs(analyze_use_case, repository) -> None:
    command = AnalyzeProductCommand(
        description="A printed t-shirt",
        images=[("front.png", b"\x89PNG-bytes", "image/png")],
    )
    analysis_id = await analyze_use_case.handle(command)
    analysis = await repository.get(analysis_id)
    assert analysis is not None
    assert len(analysis.product_input.image_refs) == 1


async def test_score_uses_injected_signal_values(analyze_use_case, repository) -> None:
    # signal_providers fixture: TREND 80 -> normalized 80; GROWTH 5 -> 50;
    # GEOGRAPHIC 60; SEASONALITY 70; CONSUMER 50.
    # total = .30*80 + .25*50 + .20*60 + .15*70 + .10*50 = 64.0
    analysis_id = await analyze_use_case.handle(AnalyzeProductCommand(description="x", images=[]))
    analysis = await repository.get(analysis_id)
    assert analysis is not None
    assert analysis.score.total == pytest.approx(64.0)


async def test_get_use_case_returns_view(analyze_use_case, get_use_case) -> None:
    analysis_id = await analyze_use_case.handle(
        AnalyzeProductCommand(description="A wooden chair", images=[])
    )
    view = await get_use_case.handle(analysis_id)
    assert isinstance(view, AnalysisView)
    assert view.status == "completed"
    assert view.score is not None
    assert view.report is not None
    assert view.category is not None


async def test_get_unknown_analysis_raises(get_use_case) -> None:
    with pytest.raises(AnalysisNotFound):
        await get_use_case.handle(AnalysisId.new())


async def test_provider_failure_imputes_without_aborting(
    repository, progress, signal_providers
) -> None:
    """A failing provider degrades to an imputed factor; pipeline still completes."""
    import conftest  # in-test fakes
    from marketmind.application.use_cases.analyze_product import AnalyzeProductUseCase
    from marketmind.domain.services.mos_calculator import MosCalculator

    class _ExplodingTrendProvider:
        @property
        def factor(self):
            return MosFactor.TREND

        async def fetch(self, attributes):
            raise RuntimeError("trends API down")

    providers = [_ExplodingTrendProvider()] + [
        p for p in signal_providers if p.factor is not MosFactor.TREND
    ]

    use_case = AnalyzeProductUseCase(
        repository=repository,
        object_storage=conftest.InMemoryObjectStorage(),
        extractor=conftest.FakeAttributeExtractor(),
        signal_providers=providers,
        mos_calculator=MosCalculator(),
        embedding_model=conftest.FakeEmbeddingModel(),
        vector_store=conftest.InMemoryVectorStore(),
        geo_ranker=conftest.FakeGeoMarketRanker(),
        report_generator=conftest.FakeReportGenerator(),
        progress=progress,
        clock=conftest.FakeClock(),
        id_generator=conftest.FakeIdGenerator(),
    )

    analysis_id = await use_case.handle(
        AnalyzeProductCommand(description="resilient pipeline", images=[])
    )
    analysis = await repository.get(analysis_id)
    assert analysis.status is AnalysisStatus.COMPLETED
    trend_fs = next(fs for fs in analysis.score.factor_scores if fs.factor is MosFactor.TREND)
    assert trend_fs.imputed is True


async def test_extractor_failure_marks_failed_and_raises(
    repository, progress, signal_providers
) -> None:
    import conftest
    from marketmind.application.use_cases.analyze_product import AnalyzeProductUseCase
    from marketmind.domain.services.mos_calculator import MosCalculator

    class _BrokenExtractor:
        async def extract(self, description, image_refs):
            raise RuntimeError("vision LLM unavailable")

    use_case = AnalyzeProductUseCase(
        repository=repository,
        object_storage=conftest.InMemoryObjectStorage(),
        extractor=_BrokenExtractor(),
        signal_providers=signal_providers,
        mos_calculator=MosCalculator(),
        embedding_model=conftest.FakeEmbeddingModel(),
        vector_store=conftest.InMemoryVectorStore(),
        geo_ranker=conftest.FakeGeoMarketRanker(),
        report_generator=conftest.FakeReportGenerator(),
        progress=progress,
        clock=conftest.FakeClock(),
        id_generator=conftest.FakeIdGenerator(),
    )

    with pytest.raises(AnalysisPipelineError):
        await use_case.handle(AnalyzeProductCommand(description="boom", images=[]))

    # The failed analysis was persisted and a 'failed' progress event published.
    assert any(e["step"] == "failed" for e in progress.events)
