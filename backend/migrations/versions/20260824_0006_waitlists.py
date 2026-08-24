"""Create private reservation waitlists."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0006"
down_revision: str | None = "20260824_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offer_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "buyer_id", name="uq_waitlist_listing_buyer"),
    )
    op.create_index("ix_waitlist_entries_listing_id", "waitlist_entries", ["listing_id"])
    op.create_index("ix_waitlist_entries_buyer_id", "waitlist_entries", ["buyer_id"])
    op.create_index("ix_waitlist_entries_status", "waitlist_entries", ["status"])


def downgrade() -> None:
    op.drop_table("waitlist_entries")
