"""Real (stub) S3 / S3-compatible object storage.

Implements :class:`ObjectStorage` against an S3 (or MinIO-style ``S3_ENDPOINT_URL``)
bucket via a boto3 client. The ``boto3`` SDK is not imported at module level —
the client is injected, so this module imports without boto3 installed; the
offline default is :class:`LocalFilesystemObjectStorage`. Stubbed: raises
``NotImplementedError`` until wired in.
"""

from __future__ import annotations

import uuid
from typing import Any

from marketmind.application.ports.ports import ObjectStorage


class S3ObjectStorage(ObjectStorage):
    """Blob storage backed by an S3-compatible bucket."""

    def __init__(self, client: Any, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def store(
        self, filename: str, data: bytes, content_type: str
    ) -> str:
        # TODO: key = f"{uuid.uuid4().hex}-{filename}";
        #   await asyncio.to_thread(self._client.put_object, Bucket=self._bucket,
        #       Key=key, Body=data, ContentType=content_type); return the key/URL.
        _ = uuid  # keep the import meaningful for the intended impl
        raise NotImplementedError(
            "S3ObjectStorage requires AWS/S3 credentials and a configured client; "
            "use LocalFilesystemObjectStorage in offline/fake mode."
        )

    async def load(self, ref: str) -> bytes:
        # TODO: obj = await asyncio.to_thread(self._client.get_object,
        #   Bucket=self._bucket, Key=<key from ref>); return obj["Body"].read().
        raise NotImplementedError(
            "S3ObjectStorage.load is not implemented; "
            "use LocalFilesystemObjectStorage in offline/fake mode."
        )
