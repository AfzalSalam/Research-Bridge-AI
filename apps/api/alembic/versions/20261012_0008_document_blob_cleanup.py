"""Retain private object cleanup intent after account deletion."""

import sqlalchemy as sa

from alembic import op

revision = "20261012_0008"
down_revision = "20261012_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_blobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("bucket", sa.String(63), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("last_error", sa.String(100)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_document_blobs_available_at", "document_blobs", ["available_at"]
    )


def downgrade() -> None:
    op.drop_table("document_blobs")
