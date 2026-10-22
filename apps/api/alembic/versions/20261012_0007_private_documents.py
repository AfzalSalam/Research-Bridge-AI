"""Private document processing records and durable leases."""

import sqlalchemy as sa

from alembic import op

revision = "20261012_0007"
down_revision = "20261011_0006"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column(
            name,
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        for name in ("created_at", "updated_at")
    ]


def upgrade() -> None:
    op.create_table(
        "research_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("account_owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "paper_id",
            sa.Uuid(),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_research_documents_owner_id", "research_documents", ["owner_id"]
    )
    op.create_index(
        "ix_research_documents_paper_id", "research_documents", ["paper_id"]
    )
    op.create_table(
        "document_pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("research_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("chunks", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "number"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_table(
        "document_jobs",
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
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("last_error", sa.String(100), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_document_jobs_status", "document_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("document_jobs")
    op.drop_table("document_pages")
    op.drop_table("research_documents")
