"""pgvector-backed ``VectorStore`` (cosine ANN over ``analyzed_product``).

Uses the HNSW index defined in the migration. ``query_comparables`` sets
``hnsw.ef_search`` per-query for recall/latency tuning, applies optional
``category`` / ``region`` metadata filters, and orders by cosine distance
(``<=>``). Selected when ``provider_mode == "real"``; the offline default is
``InMemoryVectorStore``.

NOTE: this adapter assumes the embedding row's existence is owned here. The
analysis row (FK target) must already be persisted by the repository; in the
pipeline the use case saves the aggregate before/with the embedding step.
"""

from __future__ import annotations

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketmind.application.ports.ports import VectorStore
from marketmind.domain.model.embedding import ProductEmbedding
from marketmind.domain.model.identifiers import AnalysisId


class PgVectorStore(VectorStore):
    """Cosine similarity search over product embeddings using pgvector + HNSW."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        dimensions: int,
    ) -> None:
        self._session_factory = session_factory
        self._dimensions = dimensions
        # ef_search trades recall for latency at query time; conservative default.
        self._ef_search = 64

    @staticmethod
    def _to_vector_literal(vector: tuple[float, ...]) -> str:
        """pgvector text input format: ``[v0,v1,...]``."""
        return "[" + ",".join(repr(float(v)) for v in vector) + "]"

    async def upsert(
        self,
        analysis_id: AnalysisId,
        embedding: ProductEmbedding,
        metadata: dict,
    ) -> None:
        if len(embedding.vector) != self._dimensions:
            raise ValueError(
                f"Embedding dimensionality {len(embedding.vector)} != configured "
                f"{self._dimensions}"
            )
        vector_literal = self._to_vector_literal(embedding.vector)
        search_text = " ".join(
            str(v)
            for v in (
                metadata.get("description", ""),
                metadata.get("category", ""),
                metadata.get("subcategory", ""),
                *(metadata.get("keywords") or []),
            )
            if v
        )
        stmt = text(
            """
            INSERT INTO analyzed_product
                (analysis_id, embedding, embedding_model, embedding_version,
                 mos_score, metadata, search_text)
            VALUES
                (:analysis_id, :embedding, :model, :version,
                 :mos_score, :metadata, :search_text)
            ON CONFLICT (analysis_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                embedding_version = EXCLUDED.embedding_version,
                mos_score = EXCLUDED.mos_score,
                metadata = EXCLUDED.metadata,
                search_text = EXCLUDED.search_text
            """
        ).bindparams(bindparam("metadata", type_=_JSONB()))
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    stmt,
                    {
                        "analysis_id": analysis_id.value,
                        "embedding": vector_literal,
                        "model": embedding.model,
                        "version": embedding.version,
                        "mos_score": metadata.get("mos_score"),
                        "metadata": metadata,
                        "search_text": search_text,
                    },
                )

    async def query_comparables(
        self,
        embedding: ProductEmbedding,
        *,
        k: int,
        filters: dict,
    ) -> list[dict]:
        vector_literal = self._to_vector_literal(embedding.vector)
        params: dict = {"query": vector_literal, "k": max(k, 0)}

        where_clauses: list[str] = []
        category = filters.get("category")
        if category is not None:
            where_clauses.append("metadata->>'category' = :category")
            params["category"] = category
        region = filters.get("region")
        if region is not None:
            where_clauses.append("metadata->>'region' = :region")
            params["region"] = region

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query_sql = text(
            f"""
            SELECT analysis_id,
                   embedding_model,
                   embedding_version,
                   mos_score,
                   metadata,
                   1 - (embedding <=> :query) AS similarity,
                   (embedding <=> :query) AS distance
            FROM analyzed_product
            {where_sql}
            ORDER BY embedding <=> :query
            LIMIT :k
            """
        )

        async with self._session_factory() as session:
            # Per-query ANN recall tuning.
            await session.execute(
                text("SET LOCAL hnsw.ef_search = :ef"), {"ef": self._ef_search}
            )
            result = await session.execute(query_sql, params)
            rows = result.mappings().all()

        return [
            {
                "analysis_id": str(row["analysis_id"]),
                "similarity": float(row["similarity"]),
                "distance": float(row["distance"]),
                "model": row["embedding_model"],
                "version": row["embedding_version"],
                "mos_score": row["mos_score"],
                "metadata": dict(row["metadata"] or {}),
            }
            for row in rows
        ]


def _JSONB():  # noqa: N802 - thin lazy import wrapper
    from sqlalchemy.dialects.postgresql import JSONB

    return JSONB()
