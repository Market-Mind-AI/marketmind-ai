"""In-memory progress publisher backing the SSE stream.

Implements :class:`ProgressPublisher` with one :class:`asyncio.Queue` per
analysis id. ``publish`` enqueues a step event; ``subscribe`` returns an async
iterator draining that queue. A sentinel (``None``) enqueued on the terminal
``completed``/``failed`` step closes the stream cleanly.

This is process-local (single-instance) — adequate for the MVP/offline default.
A distributed deployment would back this with Redis pub/sub or similar.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from marketmind.application.ports.ports import ProgressPublisher
from marketmind.domain.model.identifiers import AnalysisId

# Steps after which the per-analysis stream should be closed.
_TERMINAL_STEPS = frozenset({"completed", "failed"})

# Sentinel signalling end-of-stream to subscribers.
_END = None


class InMemoryProgressPublisher(ProgressPublisher):
    """Per-analysis asyncio.Queue fan-in for pipeline progress events."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[dict | None]] = {}

    def _queue_for(self, analysis_id: AnalysisId) -> asyncio.Queue[dict | None]:
        key = str(analysis_id)
        queue = self._queues.get(key)
        if queue is None:
            queue = asyncio.Queue()
            self._queues[key] = queue
        return queue

    async def publish(self, analysis_id: AnalysisId, step: str, detail: str) -> None:
        queue = self._queue_for(analysis_id)
        await queue.put({"analysis_id": str(analysis_id), "step": step, "detail": detail})
        if step in _TERMINAL_STEPS:
            await queue.put(_END)

    async def subscribe(self, analysis_id: AnalysisId) -> AsyncIterator[dict]:
        queue = self._queue_for(analysis_id)
        try:
            while True:
                event = await queue.get()
                if event is _END:
                    break
                yield event
        finally:
            # Best-effort cleanup once the subscriber detaches on a terminal stream.
            self._queues.pop(str(analysis_id), None)
