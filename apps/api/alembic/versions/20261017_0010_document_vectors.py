"""Private page vectors; SQLite JSON is for lifecycle tests only."""

import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR

from alembic import op

revision = "20261017_0010"
down_revision = "20261015_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    if postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "document_vectors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "page_id",
            sa.Uuid(),
            sa.ForeignKey("document_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("embedding", VECTOR(1536) if postgres else sa.JSON(), nullable=False),
        sa.UniqueConstraint("page_id", "start", "model"),
        sa.CheckConstraint("start >= 0 AND end_offset > start", name="valid_offsets"),
    )
    op.create_index("ix_document_vectors_page_id", "document_vectors", ["page_id"])


def downgrade() -> None:
    op.drop_table("document_vectors")
    # The shared vector extension may be used by other tables; retain it.
