"""Composition root (Dependency Injection container).

This is the single place where concrete adapters are instantiated and wired
into the application use cases. Nothing else in the codebase constructs
adapters. The container reads :class:`Settings` and, per the ``provider_mode``
toggle, selects fakes (the offline default) or real adapters.

The container exposes:
  * ``build_analyze_use_case()`` -> ``AnalyzeProductUseCase``
  * ``build_get_use_case()``     -> ``GetAnalysisUseCase``
  * ``progress_publisher``       -> shared ``ProgressPublisher`` (for SSE)
  * ``pdf_renderer``             -> shared ``PdfRenderer``

Adapter classes are imported lazily inside the build methods so that selecting
a given mode only pulls in the dependencies that mode actually needs (e.g. the
Anthropic/Cohere SDKs are never imported in fake mode).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
from marketmind.application.use_cases.analyze_product import AnalyzeProductUseCase
from marketmind.application.use_cases.get_analysis import GetAnalysisUseCase
from marketmind.domain.model.identifiers import AnalysisId
from marketmind.domain.services.mos_calculator import MosCalculator
from marketmind.infrastructure.config.settings import Settings


class SystemClock:
    """Real wall-clock adapter for the :class:`Clock` port (UTC, tz-aware)."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    """Random-UUID adapter for the :class:`IdGenerator` port."""

    def new_analysis_id(self) -> AnalysisId:
        return AnalysisId(uuid.uuid4())


class Container:
    """Composition root: builds and wires every adapter and use case.

    A single Container instance is created at app startup (lifespan) and shared
    for the process lifetime. Stateful fakes (in-memory repo / vector store /
    progress publisher) are therefore process singletons, as intended.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # --- shared infrastructure singletons ---------------------------
        self.clock: Clock = SystemClock()
        self.id_generator: IdGenerator = UuidGenerator()
        self.mos_calculator = MosCalculator()

        self.object_storage: ObjectStorage = self._build_object_storage()
        self.repository: AnalysisRepository = self._build_repository()
        self.vector_store: VectorStore = self._build_vector_store()
        self.progress_publisher: ProgressPublisher = self._build_progress_publisher()
        self.pdf_renderer: PdfRenderer = self._build_pdf_renderer()

        self.extractor: ProductAttributeExtractor = self._build_extractor()
        self.report_generator: ReportGenerator = self._build_report_generator()
        self.embedding_model: EmbeddingModel = self._build_embedding_model()
        self.signal_providers: list[MarketSignalProvider] = self._build_signal_providers()
        self.geo_ranker: GeoMarketRanker = self._build_geo_ranker()

    # ------------------------------------------------------------------
    # Public factory methods consumed by the inbound adapter.
    # ------------------------------------------------------------------
    def build_analyze_use_case(self) -> AnalyzeProductUseCase:
        return AnalyzeProductUseCase(
            repository=self.repository,
            object_storage=self.object_storage,
            extractor=self.extractor,
            signal_providers=self.signal_providers,
            mos_calculator=self.mos_calculator,
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
            geo_ranker=self.geo_ranker,
            report_generator=self.report_generator,
            progress=self.progress_publisher,
            clock=self.clock,
            id_generator=self.id_generator,
            weights=None,
        )

    def build_get_use_case(self) -> GetAnalysisUseCase:
        return GetAnalysisUseCase(repository=self.repository)

    @property
    def is_fake(self) -> bool:
        return self.settings.provider_mode == "fake"

    # ------------------------------------------------------------------
    # Adapter builders (fake = offline default, real = stubbed adapters).
    # ------------------------------------------------------------------
    def _build_object_storage(self) -> ObjectStorage:
        from marketmind.infrastructure.storage.local_filesystem import (
            LocalFilesystemObjectStorage,
        )

        if self.is_fake:
            return LocalFilesystemObjectStorage(
                self.settings.storage_root,
                base_url=self.settings.storage_base_url,
            )
        from marketmind.infrastructure.storage.s3_storage import S3ObjectStorage

        return S3ObjectStorage(client=None, bucket="marketmind")

    def _build_repository(self) -> AnalysisRepository:
        if self.is_fake or self.settings.use_in_memory_persistence:
            from marketmind.infrastructure.persistence.in_memory_analysis_repository import (
                InMemoryAnalysisRepository,
            )

            return InMemoryAnalysisRepository()

        from marketmind.infrastructure.persistence.sqlalchemy_analysis_repository import (
            SqlAlchemyAnalysisRepository,
        )

        return SqlAlchemyAnalysisRepository(self._session_factory())

    def _build_vector_store(self) -> VectorStore:
        if self.is_fake or self.settings.use_in_memory_persistence:
            from marketmind.infrastructure.persistence.in_memory_vector_store import (
                InMemoryVectorStore,
            )

            return InMemoryVectorStore()

        from marketmind.infrastructure.persistence.pgvector_store import PgVectorStore

        return PgVectorStore(
            self._session_factory(),
            dimensions=self.settings.embedding_dimensions,
        )

    def _build_progress_publisher(self) -> ProgressPublisher:
        from marketmind.infrastructure.progress.in_memory import (
            InMemoryProgressPublisher,
        )

        return InMemoryProgressPublisher()

    def _build_pdf_renderer(self) -> PdfRenderer:
        if self.is_fake:
            from marketmind.infrastructure.pdf.html_renderer import HtmlPdfRenderer

            return HtmlPdfRenderer()
        from marketmind.infrastructure.pdf.weasyprint_renderer import (
            WeasyPrintPdfRenderer,
        )

        return WeasyPrintPdfRenderer()

    def _build_extractor(self) -> ProductAttributeExtractor:
        if self.is_fake:
            from marketmind.infrastructure.llm.fake import FakeAttributeExtractor

            return FakeAttributeExtractor()

        from marketmind.infrastructure.llm.claude_extractor import (
            ClaudeAttributeExtractor,
        )

        return ClaudeAttributeExtractor(
            client=self._anthropic_client(),
            storage=self.object_storage,
            model=self.settings.extraction_model,
        )

    def _build_report_generator(self) -> ReportGenerator:
        if self.is_fake:
            from marketmind.infrastructure.llm.fake import FakeReportGenerator

            return FakeReportGenerator()

        from marketmind.infrastructure.llm.claude_report import ClaudeReportGenerator

        return ClaudeReportGenerator(
            client=self._anthropic_client(),
            model=self.settings.report_model,
        )

    def _build_embedding_model(self) -> EmbeddingModel:
        if self.is_fake:
            from marketmind.infrastructure.embeddings.fake import FakeEmbeddingModel

            return FakeEmbeddingModel(
                dimensions=self.settings.embedding_dimensions,
            )

        from marketmind.infrastructure.embeddings.cohere_embeddings import (
            CohereEmbeddingModel,
        )

        return CohereEmbeddingModel(
            client=self._cohere_client(),
            model=self.settings.embedding_model,
        )

    def _build_signal_providers(self) -> list[MarketSignalProvider]:
        if self.is_fake:
            from marketmind.infrastructure.connectors.fake import (
                FakeConsumerProvider,
                FakeGeographicProvider,
                FakeMacroProvider,
                FakeSeasonalityProvider,
                FakeTrendsProvider,
            )

            return [
                FakeTrendsProvider(),
                FakeMacroProvider(),
                FakeGeographicProvider(),
                FakeSeasonalityProvider(),
                FakeConsumerProvider(),
            ]

        client = self._httpx_client()
        from marketmind.infrastructure.connectors.dataforseo_trends import (
            DataForSeoTrendsProvider,
        )
        from marketmind.infrastructure.connectors.ebay_marketplace import (
            EbayMarketplaceProvider,
        )
        from marketmind.infrastructure.connectors.world_bank_macro import (
            WorldBankMacroProvider,
        )

        return [
            DataForSeoTrendsProvider(
                client,
                login=self.settings.dataforseo_login or "",
                password=self.settings.dataforseo_password or "",
            ),
            WorldBankMacroProvider(client),
            EbayMarketplaceProvider(client, app_id=self.settings.ebay_app_id or ""),
        ]

    def _build_geo_ranker(self) -> GeoMarketRanker:
        if self.is_fake:
            from marketmind.infrastructure.connectors.fake import FakeGeoMarketRanker

            return FakeGeoMarketRanker()

        from marketmind.infrastructure.connectors.world_bank_macro import (
            WorldBankGeoMarketRanker,
        )

        return WorldBankGeoMarketRanker(self._httpx_client())

    # ------------------------------------------------------------------
    # Lazily-built real-mode clients (never imported in fake mode).
    # ------------------------------------------------------------------
    def _session_factory(self):
        from sqlalchemy.ext.asyncio import (
            async_sessionmaker,
            create_async_engine,
        )

        if not hasattr(self, "_cached_session_factory"):
            engine = create_async_engine(self.settings.database_url)
            self._cached_session_factory = async_sessionmaker(engine, expire_on_commit=False)
        return self._cached_session_factory

    def _anthropic_client(self):
        import anthropic

        if not hasattr(self, "_cached_anthropic"):
            self._cached_anthropic = anthropic.AsyncAnthropic(
                api_key=self.settings.anthropic_api_key
            )
        return self._cached_anthropic

    def _cohere_client(self):
        import cohere

        if not hasattr(self, "_cached_cohere"):
            self._cached_cohere = cohere.AsyncClientV2(api_key=self.settings.cohere_api_key)
        return self._cached_cohere

    def _httpx_client(self):
        import httpx

        if not hasattr(self, "_cached_httpx"):
            self._cached_httpx = httpx.AsyncClient()
        return self._cached_httpx

    async def aclose(self) -> None:
        """Release any real-mode network/db resources held by the container."""
        client = getattr(self, "_cached_httpx", None)
        if client is not None:
            await client.aclose()


def build_container(settings: Settings | None = None) -> Container:
    """Convenience factory used by the app factory and tests."""
    from marketmind.infrastructure.config.settings import get_settings

    return Container(settings or get_settings())
