"""Shared pytest fixtures.

The whole test suite runs OFFLINE against only the ``domain`` and
``application`` layers plus the in-test FAKE adapters defined here. No DB, no
network, no API keys, no third-party packages are required (pytest /
pytest-asyncio aside).

The fakes implement the application ports *structurally* (they satisfy the
``@runtime_checkable`` Protocols) but are defined here rather than imported from
``infrastructure`` so the suite passes before any infrastructure is built.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

# --- make the src-layout package importable without installation ------------
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from marketmind.application.use_cases.analyze_product import (  # noqa: E402
    AnalyzeProductUseCase,
)
from marketmind.application.use_cases.get_analysis import (  # noqa: E402
    GetAnalysisUseCase,
)
from marketmind.domain.model.analysis import Analysis  # noqa: E402
from marketmind.domain.model.embedding import ProductEmbedding  # noqa: E402
from marketmind.domain.model.identifiers import AnalysisId  # noqa: E402
from marketmind.domain.model.product import ProductAttributes  # noqa: E402
from marketmind.domain.model.report import (  # noqa: E402
    Citation,
    LaunchWindow,
    MarketRecommendation,
    OpportunityReport,
    PriceBand,
)
from marketmind.domain.model.scoring import MosFactor  # noqa: E402
from marketmind.domain.services.mos_calculator import MosCalculator  # noqa: E402


# ---------------------------------------------------------------------------
# Fake adapters (in-memory / deterministic; offline)
# ---------------------------------------------------------------------------
class FakeClock:
    def __init__(self, fixed: datetime | None = None) -> None:
        self._fixed = fixed or datetime(2024, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._fixed


class FakeIdGenerator:
    """Deterministic, monotonically increasing AnalysisId generator."""

    def __init__(self) -> None:
        self._n = 0

    def new_analysis_id(self) -> AnalysisId:
        self._n += 1
        return AnalysisId(uuid.UUID(int=self._n))


class InMemoryAnalysisRepository:
    def __init__(self) -> None:
        self._store: dict[str, Analysis] = {}

    async def save(self, analysis: Analysis) -> None:
        self._store[str(analysis.id)] = analysis

    async def get(self, analysis_id: AnalysisId) -> Analysis | None:
        return self._store.get(str(analysis_id))


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._n = 0

    async def store(self, filename: str, data: bytes, content_type: str) -> str:
        self._n += 1
        ref = f"mem://{self._n}/{filename}"
        self._blobs[ref] = data
        return ref

    async def load(self, ref: str) -> bytes:
        return self._blobs[ref]


class FakeAttributeExtractor:
    async def extract(
        self, description: str, image_refs: list[str]
    ) -> ProductAttributes:
        return ProductAttributes(
            category="accessories",
            subcategory="bags",
            materials=("leather",),
            color="brown",
            style="minimalist",
            key_features=("durable", "handmade"),
            suggested_keywords=("leather bag", "handmade"),
            confidence=0.9,
        )


class _FakeSignalProvider:
    """A single-factor provider returning a deterministic value."""

    def __init__(self, factor: MosFactor, value: float) -> None:
        self._factor = factor
        self._value = value

    @property
    def factor(self) -> MosFactor:
        return self._factor

    async def fetch(self, attributes: ProductAttributes) -> float:
        return self._value


class FakeGeoMarketRanker:
    async def rank(
        self,
        attributes: ProductAttributes,
        signals: dict[MosFactor, float | None],
    ) -> list[MarketRecommendation]:
        return [
            MarketRecommendation(
                country_code="US",
                country_name="United States",
                score=82.0,
                rationale="Large addressable market.",
            ),
            MarketRecommendation(
                country_code="DE",
                country_name="Germany",
                score=71.0,
                rationale="Strong demand for the category.",
            ),
        ]


class FakeEmbeddingModel:
    def __init__(self, *, dimensions: int = 8) -> None:
        self._dimensions = dimensions

    async def embed(
        self,
        description: str,
        attributes: ProductAttributes,
        image_refs: list[str],
    ) -> ProductEmbedding:
        vec = tuple(float((i + len(description)) % 7) for i in range(self._dimensions))
        return ProductEmbedding(vector=vec, model="fake-embed", version=1)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._items: list[dict] = []

    async def upsert(self, analysis_id, embedding, metadata: dict) -> None:
        self._items.append(
            {"id": str(analysis_id), "vector": embedding.vector, **metadata}
        )

    async def query_comparables(
        self, embedding, *, k: int, filters: dict
    ) -> list[dict]:
        return self._items[:k]


class FakeReportGenerator:
    async def generate(self, analysis: Analysis, comparables: list[dict]) -> OpportunityReport:
        tier = analysis.score.tier if analysis.score else "moderate"
        return OpportunityReport(
            verdict=f"{tier} opportunity",
            summary="A fake but well-formed report for offline testing.",
            markets=analysis.markets
            or (
                MarketRecommendation(
                    country_code="US",
                    country_name="United States",
                    score=80.0,
                    rationale="Primary market.",
                ),
            ),
            price_band=PriceBand(
                low=Decimal("19.99"),
                high=Decimal("49.99"),
                currency="USD",
                note="Mid-market positioning.",
            ),
            launch_window=LaunchWindow(label="Q4", peak_note="Holiday season peak."),
            recommendations=("Launch in the US first.",),
            citations=(
                Citation(source="FakeTrends", detail="Rising interest", as_of="2024-01"),
            ),
        )


class InMemoryProgressPublisher:
    """Records published events so tests can assert per-step progress."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def publish(self, analysis_id, step: str, detail: str) -> None:
        self.events.append(
            {"analysis_id": str(analysis_id), "step": step, "detail": detail}
        )

    def subscribe(self, analysis_id):  # pragma: no cover - not exercised here
        async def _gen():
            for e in self.events:
                yield e

        return _gen()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def progress() -> InMemoryProgressPublisher:
    return InMemoryProgressPublisher()


@pytest.fixture
def repository() -> InMemoryAnalysisRepository:
    return InMemoryAnalysisRepository()


@pytest.fixture
def signal_providers() -> list[_FakeSignalProvider]:
    """One provider per factor (five), with deterministic raw values."""
    return [
        _FakeSignalProvider(MosFactor.TREND, 80.0),
        _FakeSignalProvider(MosFactor.GROWTH, 5.0),
        _FakeSignalProvider(MosFactor.GEOGRAPHIC, 60.0),
        _FakeSignalProvider(MosFactor.SEASONALITY, 70.0),
        _FakeSignalProvider(MosFactor.CONSUMER, 50.0),
    ]


@pytest.fixture
def analyze_use_case(
    repository: InMemoryAnalysisRepository,
    progress: InMemoryProgressPublisher,
    signal_providers: list[_FakeSignalProvider],
) -> AnalyzeProductUseCase:
    """Build AnalyzeProductUseCase wired entirely with fakes (offline)."""
    return AnalyzeProductUseCase(
        repository=repository,
        object_storage=InMemoryObjectStorage(),
        extractor=FakeAttributeExtractor(),
        signal_providers=signal_providers,
        mos_calculator=MosCalculator(),
        embedding_model=FakeEmbeddingModel(),
        vector_store=InMemoryVectorStore(),
        geo_ranker=FakeGeoMarketRanker(),
        report_generator=FakeReportGenerator(),
        progress=progress,
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
    )


@pytest.fixture
def get_use_case(
    repository: InMemoryAnalysisRepository,
) -> GetAnalysisUseCase:
    return GetAnalysisUseCase(repository=repository)
