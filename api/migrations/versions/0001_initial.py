"""initial schema: vector extension, analysis + analyzed_product, HNSW + FTS.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18

Creates the pgvector extension, the ``analysis`` aggregate table, the
``analyzed_product`` vector-search projection (pgvector embedding, JSONB
metadata, generated tsvector), and the HNSW (cosine) + GIN (full-text) indexes.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1024


def upgrade() -> None:
    # pgvector extension (required before any Vector column).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_refs", postgresql.JSONB(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=True),
        sa.Column("enrichment", postgresql.JSONB(), nullable=True),
        sa.Column("score", postgresql.JSONB(), nullable=True),
        sa.Column("markets", postgresql.JSONB(), nullable=True),
        sa.Column("embedding", postgresql.JSONB(), nullable=True),
        sa.Column("report", postgresql.JSONB(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.create_index("analysis_status_idx", "analysis", ["status"])

    op.create_table(
        "analyzed_product",
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding_version", sa.Integer(), nullable=False),
        sa.Column("mos_score", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "search_document",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(search_text, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
    )

    # B-tree on category for cheap equality filtering.
    op.execute(
        "CREATE INDEX analyzed_product_category_idx "
        "ON analyzed_product ((metadata->>'category'))"
    )

    # Approximate nearest-neighbour over the embedding (cosine distance).
    op.execute(
        "CREATE INDEX analyzed_product_embedding_hnsw "
        "ON analyzed_product USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # Full-text GIN over the generated tsvector for hybrid search.
    op.execute(
        "CREATE INDEX analyzed_product_search_gin "
        "ON analyzed_product USING gin (search_document)"
    )


def downgrade() -> None:
    op.drop_index("analyzed_product_search_gin", table_name="analyzed_product")
    op.drop_index("analyzed_product_embedding_hnsw", table_name="analyzed_product")
    op.drop_index("analyzed_product_category_idx", table_name="analyzed_product")
    op.drop_table("analyzed_product")
    op.drop_index("analysis_status_idx", table_name="analysis")
    op.drop_table("analysis")
    op.execute("DROP EXTENSION IF EXISTS vector")
