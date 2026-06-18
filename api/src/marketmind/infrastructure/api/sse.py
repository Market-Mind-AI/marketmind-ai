"""Server-Sent Events bridge for pipeline progress.

Adapts the application ``ProgressPublisher.subscribe`` async iterator (which
yields plain ``dict`` events) into an ``sse_starlette`` ``EventSourceResponse``
so browsers can stream live analysis progress. No domain or use-case logic
lives here — it is pure transport.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from sse_starlette.sse import EventSourceResponse

from marketmind.application.ports.ports import ProgressPublisher
from marketmind.domain.model.identifiers import AnalysisId

# Steps after which the stream is closed (terminal pipeline outcomes).
_TERMINAL_STEPS = frozenset({"completed", "failed"})


async def _event_source(
    progress: ProgressPublisher, analysis_id: AnalysisId
) -> AsyncIterator[dict]:
    async for event in progress.subscribe(analysis_id):
        step = str(event.get("step", ""))
        yield {
            "event": "progress",
            "data": json.dumps(event, default=str),
        }
        if step in _TERMINAL_STEPS:
            break


def analysis_event_stream(
    progress: ProgressPublisher, analysis_id: AnalysisId
) -> EventSourceResponse:
    """Return an SSE response streaming progress events for one analysis."""
    return EventSourceResponse(_event_source(progress, analysis_id))
