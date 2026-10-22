"""Private completed reading exchanges, removed with document or account."""

import sqlalchemy as sa

from alembic import op

revision = "20261022_0013"
down_revision = "20261021_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reading_answers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("account_owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("research_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("disclosure_version", sa.String(60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("owner_id", "request_id"),
    )
    op.create_index(
        "ix_reading_answers_owner_document_created",
        "reading_answers",
        ["owner_id", "document_id", "created_at"],
    )


def downgrade():
    op.drop_table("reading_answers")
