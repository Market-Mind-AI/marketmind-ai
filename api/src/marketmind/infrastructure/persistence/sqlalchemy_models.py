"""SQLAlchemy 2.0 declarative ORM models (the database schema).

These are deliberately kept SEPARATE from the domain entities/VOs: the domain
``Analysis`` aggregate is a pure stdlib dataclass and never imports SQLAlchemy.
The repository (``sqlalchemy_analysis_repository``) maps between the two. No
class in this module implements an application port.

Two tables:

* ``analysis`` — the aggregate root snapshot. Scalar lifecycle columns plus the
  rich value objects serialized into JSONB (attributes, enrichment, score,
  markets, report). The embedding vector lives on the companion table.
* ``analyzed_product`` — the vector-search projection (one row per analysis):
  a pgvector ``Vector(1024)`` embedding, JSONB ``metadata``, the scalar
  ``mos_score`` and embedding provenance, and a GENERATED ``tsvector`` column
  (``search_document``) enabling hybrid lexical + vector retrieval.

Index DDL note (created in the Alembic migration, not by ``create_all``):

    -- Approximate nearest-neighbour over the embedding (cosine):
    CREATE INDEX analyzed_product_embedding_hnsw
        ON analyzed_product
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);

    -- Full-text GIN over the generated tsvector:
    CREATE INDEX analyzed_product_search_gin
        ON analyzed_product USING gin (search_document);
"""

from __future__ import annotations

import datetime as _dt
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# Embedding dimensionality — matches Settings.embedding_dimensions default (1024)
# and the pgvector column width. Kept as a module constant so the migration and
# the PgVectorStore can reference a single source of truth.
EMBEDDING_DIMENSIONS = 1024


class Base(DeclarativeBase):
    """Declarative base for all MarketMind ORM models."""


class AnalysisModel(Base):
    """Persistent snapshot of the ``Analysis`` aggregate root."""

    __tablename__ = "analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ----- ProductInput (flattened) -----
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # ----- rich value objects serialized as JSONB (nullable until produced) ---
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enrichment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    score: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    markets: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped[AnalyzedProductModel | None] = relationship(
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AnalyzedProductModel(Base):
    """Vector-search projection: one embedded product per analysis."""

    __tablename__ = "analyzed_product"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # pgvector dense embedding (cosine ANN target).
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_version: Mapped[int] = mapped_column(nullable=False)

    mos_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Filter / display metadata (category, subcategory, region, keywords, ...).
    product_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Lexical search material kept denormalized for the generated tsvector.
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Generated full-text column for hybrid (lexical + vector) retrieval.
    search_document: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(search_text, ''))", persisted=True),
        nullable=True,
    )

    analysis: Mapped[AnalysisModel] = relationship(back_populates="product")

    __table_args__ = (Index("analyzed_product_category_idx", product_metadata["category"].astext),)
