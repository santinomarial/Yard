"""Create reports, moderator roles, and immutable admin audit actions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0010"
down_revision: str | None = "20260824_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("reported_user_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("assigned_admin_id", sa.Uuid(), nullable=True),
        sa.Column("resolution", sa.String(length=80), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN listing_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN reported_user_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN message_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_report_exactly_one_target",
        ),
        sa.ForeignKeyConstraint(["assigned_admin_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "reporter_id",
        "target_type",
        "listing_id",
        "reported_user_id",
        "message_id",
        "reason",
        "severity",
        "status",
        "assigned_admin_id",
    ):
        op.create_index(f"ix_reports_{column}", "reports", [column])
    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("admin_id", "report_id", "action_type", "target_id"):
        op.create_index(f"ix_admin_actions_{column}", "admin_actions", [column])


def downgrade() -> None:
    op.drop_table("admin_actions")
    op.drop_table("reports")
    op.drop_column("users", "is_admin")
