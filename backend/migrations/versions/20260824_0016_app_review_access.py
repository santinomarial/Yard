"""Add single-use App Review access invitations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0016"
down_revision: str | None = "20260824_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("review_access_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "app_review_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=140), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_by", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["consumed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_app_review_invites_code_hash", "app_review_invites", ["code_hash"])
    op.create_index("ix_app_review_invites_expires_at", "app_review_invites", ["expires_at"])
    op.create_index("ix_app_review_invites_consumed_by", "app_review_invites", ["consumed_by"])


def downgrade() -> None:
    op.drop_table("app_review_invites")
    op.drop_column("users", "review_access_expires_at")
