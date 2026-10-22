"""Public researcher contact evidence.

Revision ID: 20261010_0005
Revises: 20260801_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0005"
down_revision: str | None = "20260801_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_contact_lookups",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "author_id",
            sa.Uuid(),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_public_contact_lookups_author_id", "public_contact_lookups", ["author_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_contact_lookups_author_id", table_name="public_contact_lookups"
    )
    op.drop_table("public_contact_lookups")
