"""Create privacy-aware pickup coordination state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0009"
down_revision: str | None = "20260824_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pickup_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_by", sa.Uuid(), nullable=False),
        sa.Column("meeting_zone", sa.String(length=100), nullable=False),
        sa.Column("proposed_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("buyer_arrival", sa.String(length=20), nullable=False),
        sa.Column("seller_arrival", sa.String(length=20), nullable=False),
        sa.Column("buyer_eta_minutes", sa.Integer(), nullable=True),
        sa.Column("seller_eta_minutes", sa.Integer(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("buyer_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seller_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pickup_sessions_reservation_id",
        "pickup_sessions",
        ["reservation_id"],
        unique=True,
    )
    op.create_index("ix_pickup_sessions_proposed_by", "pickup_sessions", ["proposed_by"])
    op.create_index("ix_pickup_sessions_proposed_for", "pickup_sessions", ["proposed_for"])
    op.create_index("ix_pickup_sessions_status", "pickup_sessions", ["status"])


def downgrade() -> None:
    op.drop_table("pickup_sessions")
