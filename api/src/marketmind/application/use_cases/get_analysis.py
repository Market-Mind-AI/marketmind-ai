"""GetAnalysisUseCase — query handler returning an AnalysisView."""

from __future__ import annotations

from marketmind.application.dto import AnalysisView
from marketmind.application.errors import AnalysisNotFound
from marketmind.application.ports.ports import AnalysisRepository
from marketmind.domain.model.identifiers import AnalysisId


class GetAnalysisUseCase:
    """Fetch a single analysis and project it to an AnalysisView."""

    def __init__(self, *, repository: AnalysisRepository) -> None:
        self._repository = repository

    async def handle(self, analysis_id: AnalysisId) -> AnalysisView:
        analysis = await self._repository.get(analysis_id)
        if analysis is None:
            raise AnalysisNotFound(str(analysis_id))
        return AnalysisView.from_domain(analysis)
