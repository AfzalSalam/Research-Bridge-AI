"""Index private document page full-text search on PostgreSQL."""

from alembic import op

revision = "20261015_0009"
down_revision = "20261012_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_document_pages_search ON document_pages "
            "USING gin (to_tsvector('simple', text))"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_document_pages_search", table_name="document_pages")
