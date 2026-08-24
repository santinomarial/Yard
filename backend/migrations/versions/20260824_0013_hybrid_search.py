"""Add PostgreSQL full-text and vector search indexes."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260824_0013"
down_revision: str | None = "20260824_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        ALTER TABLE listings
        ADD COLUMN search_document tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
        ) STORED
        """
    )
    op.execute("ALTER TABLE listings ADD COLUMN embedding vector(96)")
    op.execute("CREATE INDEX ix_listings_search_document ON listings USING gin (search_document)")
    op.execute(
        "CREATE INDEX ix_listings_embedding_hnsw ON listings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_listings_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_listings_search_document")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS search_document")
