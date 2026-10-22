"""Account-backed research workspace and recipient evidence."""

import sqlalchemy as sa

from alembic import op

revision = "20261011_0006"
down_revision = "20261010_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_items",
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
        sa.Column("collection", sa.String(120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("author_ids", sa.JSON(), nullable=False),
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
        sa.UniqueConstraint("owner_id", "paper_id"),
    )
    op.create_index("ix_research_items_owner_id", "research_items", ["owner_id"])
    op.create_index("ix_research_items_paper_id", "research_items", ["paper_id"])
    op.add_column(
        "outreach_drafts", sa.Column("contact_provenance", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("outreach_drafts", "contact_provenance")
    op.drop_table("research_items")
