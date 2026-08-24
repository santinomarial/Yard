"""Create core marketplace tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "slug", name="uq_categories_parent_slug"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])
    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column(
            "condition",
            sa.Enum("NEW", "LIKE_NEW", "GOOD", "FAIR", name="listing_condition", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING_MODERATION",
                "ACTIVE",
                "RESERVED",
                "SOLD",
                "ARCHIVED",
                "REJECTED",
                "REMOVED",
                name="listing_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("pickup_zone", sa.String(length=100), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("save_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("price_cents >= 0", name="ck_listings_nonnegative_price"),
        sa.CheckConstraint(
            "(is_free = true AND price_cents = 0) OR (is_free = false AND price_cents > 0)",
            name="ck_listings_free_price_consistency",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["subcategory_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listings_seller_id", "listings", ["seller_id"])
    op.create_index("ix_listings_category_id", "listings", ["category_id"])
    op.create_index("ix_listings_subcategory_id", "listings", ["subcategory_id"])
    op.create_index("ix_listings_status", "listings", ["status"])
    op.create_index("ix_listings_status_published", "listings", ["status", "published_at"])
    op.create_index("ix_listings_category_status", "listings", ["category_id", "status"])


def downgrade() -> None:
    op.drop_table("listings")
    op.drop_table("categories")
