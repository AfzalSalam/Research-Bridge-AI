"""Durable semantic indexing and conservative owner usage reservations."""

import sqlalchemy as sa

from alembic import op

revision = "20261017_0011"
down_revision = "20261017_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_index_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("research_documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("last_error", sa.String(100)),
        sa.Column("disclosure_version", sa.String(40), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_document_index_jobs_available_at", "document_index_jobs", ["available_at"]
    )
    op.create_table(
        "embedding_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("account_owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lease_token", sa.Uuid(), nullable=False, unique=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.CheckConstraint("reserved_tokens > 0", name="positive_reservation"),
    )
    op.create_index(
        "ix_embedding_reservations_owner_day",
        "embedding_reservations",
        ["owner_id", "day"],
    )


def downgrade() -> None:
    op.drop_table("embedding_reservations")
    op.drop_table("document_index_jobs")
