"""Local-filesystem object storage (the offline default).

Implements :class:`ObjectStorage` by writing uploaded bytes under a ``data/``
root and returning an opaque ref. The ref is the stored relative path (or a
URL if ``base_url`` is set); ``load`` resolves it back to bytes. Filenames are
sanitized and uniquified to avoid collisions and path traversal.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import uuid

from marketmind.application.ports.ports import ObjectStorage

_URL_SCHEME_PREFIXES = ("http://", "https://")


def _safe_filename(filename: str) -> str:
    """Strip any directory components and unsafe characters from a filename."""
    base = os.path.basename(filename or "").strip()
    base = base.replace("\x00", "")
    if not base or base in (".", ".."):
        base = "upload"
    return base


class LocalFilesystemObjectStorage(ObjectStorage):
    """Stores blobs on the local filesystem under a data root."""

    def __init__(self, root: pathlib.Path, *, base_url: str = "") -> None:
        self._root = pathlib.Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._base_url = base_url.rstrip("/")

    async def store(self, filename: str, data: bytes, content_type: str) -> str:
        safe = _safe_filename(filename)
        # Uniquify to avoid clobbering concurrent uploads with the same name.
        key = f"{uuid.uuid4().hex}-{safe}"
        path = self._root / key

        await asyncio.to_thread(path.write_bytes, data)

        if self._base_url:
            return f"{self._base_url}/{key}"
        return key

    async def load(self, ref: str) -> bytes:
        path = self._resolve(ref)
        return await asyncio.to_thread(path.read_bytes)

    def _resolve(self, ref: str) -> pathlib.Path:
        key = ref
        if self._base_url and ref.startswith(self._base_url):
            key = ref[len(self._base_url) :].lstrip("/")
        elif ref.startswith(_URL_SCHEME_PREFIXES):
            key = ref.rsplit("/", 1)[-1]
        # Guard against traversal: keep the resolved path under the root.
        candidate = (self._root / _safe_filename(key)).resolve()
        root = self._root.resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(f"Refusing to load ref outside storage root: {ref!r}")
        return candidate
