"""Create bundles and atomic bundle reservations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0007"
down_revision: str | None = "20260824_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bundles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bundles_seller_id", "bundles", ["seller_id"])
    op.create_table(
        "bundle_items",
        sa.Column("bundle_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"]),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.PrimaryKeyConstraint("bundle_id", "listing_id"),
        sa.UniqueConstraint("listing_id", name="uq_bundle_item_listing"),
    )
    op.create_table(
        "bundle_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bundle_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("buyer_id", "idempotency_key", name="uq_bundle_reservation_buyer_key"),
    )
    op.create_index("ix_bundle_reservations_bundle_id", "bundle_reservations", ["bundle_id"])
    op.create_index("ix_bundle_reservations_buyer_id", "bundle_reservations", ["buyer_id"])
    op.add_column("reservations", sa.Column("bundle_reservation_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_reservations_bundle_reservation",
        "reservations",
        "bundle_reservations",
        ["bundle_reservation_id"],
        ["id"],
    )
    op.create_index(
        "ix_reservations_bundle_reservation_id",
        "reservations",
        ["bundle_reservation_id"],
    )


def downgrade() -> None:
    op.drop_column("reservations", "bundle_reservation_id")
    op.drop_table("bundle_reservations")
    op.drop_table("bundle_items")
    op.drop_table("bundles")
