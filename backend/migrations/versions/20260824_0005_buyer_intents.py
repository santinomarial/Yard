"""Create saves, buying intents, and explainable matches."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0005"
down_revision: str | None = "20260824_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_listings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.PrimaryKeyConstraint("user_id", "listing_id"),
    )
    op.create_table(
        "buying_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=140), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("maximum_price_cents", sa.Integer(), nullable=True),
        sa.Column("minimum_condition", sa.String(length=8), nullable=True),
        sa.Column("pickup_zone", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buying_intents_buyer_id", "buying_intents", ["buyer_id"])
    op.create_table(
        "listing_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("intent_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_components", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["intent_id"], ["buying_intents.id"]),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent_id", "listing_id", name="uq_match_intent_listing"),
    )
    op.create_index("ix_listing_matches_intent_id", "listing_matches", ["intent_id"])
    op.create_index("ix_listing_matches_listing_id", "listing_matches", ["listing_id"])


def downgrade() -> None:
    op.drop_table("listing_matches")
    op.drop_table("buying_intents")
    op.drop_table("saved_listings")
