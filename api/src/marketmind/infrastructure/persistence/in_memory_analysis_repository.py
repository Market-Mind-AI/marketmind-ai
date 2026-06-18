"""Dict-backed in-memory ``AnalysisRepository`` — the offline default.

Stores deep copies of the aggregate so callers cannot mutate persisted state
out of band (mirroring the isolation a real database transaction provides).
"""

from __future__ import annotations

import copy

from marketmind.application.ports.ports import AnalysisRepository
from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.identifiers import AnalysisId


class InMemoryAnalysisRepository(AnalysisRepository):
    """Process-local repository for tests and fully-offline runs."""

    def __init__(self) -> None:
        self._store: dict[str, Analysis] = {}

    async def save(self, analysis: Analysis) -> None:
        # Copy on write so later in-memory mutations don't retroactively change
        # what was "persisted".
        self._store[str(analysis.id)] = copy.deepcopy(analysis)

    async def get(self, analysis_id: AnalysisId) -> Analysis | None:
        stored = self._store.get(str(analysis_id))
        if stored is None:
            return None
        # Copy on read so the caller owns an isolated aggregate.
        return copy.deepcopy(stored)
