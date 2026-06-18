"""Real (stub) Cohere embedding adapter.

Implements :class:`EmbeddingModel` against the Cohere v2 embeddings API. The
``cohere`` SDK is imported lazily (only ``TYPE_CHECKING``) so this module
imports without the SDK installed; the offline default is
:class:`FakeEmbeddingModel`. Stubbed: raises ``NotImplementedError`` until a
Cohere key is wired in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from marketmind.application.ports.ports import EmbeddingModel
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.product import ProductAttributes

if TYPE_CHECKING:  # pragma: no cover - typing only
    import cohere

# Pinned embedding model id for the real adapter.
_DEFAULT_MODEL = "embed-v4.0"


class CohereEmbeddingModel(EmbeddingModel):
    """Dense product embeddings via the Cohere v2 API."""

    def __init__(
        self,
        client: "cohere.AsyncClientV2",
        *,
        model: str = _DEFAULT_MODEL,
        version: int = 1,
    ) -> None:
        self._client = client
        self._model = model
        self._version = version

    async def embed(
        self,
        description: str,
        attributes: ProductAttributes,
        image_refs: list[str],
    ) -> ProductEmbedding:
        # TODO: build a search-document input from description + attributes and
        #   call self._client.embed(model=self._model, input_type="search_document",
        #   texts=[...], embedding_types=["float"]) then wrap the returned vector
        #   in ProductEmbedding(vector=..., model=self._model, version=self._version).
        raise NotImplementedError(
            "CohereEmbeddingModel requires a Cohere API key; "
            "use FakeEmbeddingModel in offline/fake mode."
        )
