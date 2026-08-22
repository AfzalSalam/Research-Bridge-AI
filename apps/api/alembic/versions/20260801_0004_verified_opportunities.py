"""verified opportunities and durable tracker uniqueness

Revision ID: 20260801_0004
Revises: 20260801_0003
Create Date: 2026-08-01 23:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0004"
down_revision: str | None = "20260801_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add normalized opportunity evidence and owner-target idempotency."""

    with op.batch_alter_table("opportunities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_kind", sa.String(40), nullable=True))
        batch_op.add_column(
            sa.Column("evidence_confidence", sa.String(20), nullable=True)
        )
        batch_op.add_column(sa.Column("opportunity_type", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("research_fields", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("duration_text", sa.String(160), nullable=True))
        batch_op.add_column(sa.Column("eligibility_text", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("extraction_evidence", sa.JSON(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE opportunities SET source_kind = 'legacy', "
            "evidence_confidence = 'limited', opportunity_type = 'other', "
            "research_fields = '[]', extraction_evidence = '[]'"
        )
    )

    with op.batch_alter_table("opportunities", schema=None) as batch_op:
        batch_op.alter_column(
            "source_kind", existing_type=sa.String(40), nullable=False
        )
        batch_op.alter_column(
            "evidence_confidence", existing_type=sa.String(20), nullable=False
        )
        batch_op.alter_column(
            "opportunity_type", existing_type=sa.String(40), nullable=False
        )
        batch_op.alter_column(
            "research_fields", existing_type=sa.JSON(), nullable=False
        )
        batch_op.alter_column(
            "extraction_evidence", existing_type=sa.JSON(), nullable=False
        )

    with op.batch_alter_table("applications", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            batch_op.f("uq_applications_owner_id_author_id"),
            ["owner_id", "author_id"],
        )
        batch_op.create_unique_constraint(
            batch_op.f("uq_applications_owner_id_opportunity_id"),
            ["owner_id", "opportunity_id"],
        )


def downgrade() -> None:
    """Remove Phase 9 opportunity evidence and tracker uniqueness."""

    with op.batch_alter_table("applications", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("uq_applications_owner_id_opportunity_id"), type_="unique"
        )
        batch_op.drop_constraint(
            batch_op.f("uq_applications_owner_id_author_id"), type_="unique"
        )

    with op.batch_alter_table("opportunities", schema=None) as batch_op:
        batch_op.drop_column("extraction_evidence")
        batch_op.drop_column("source_updated_at")
        batch_op.drop_column("eligibility_text")
        batch_op.drop_column("duration_text")
        batch_op.drop_column("research_fields")
        batch_op.drop_column("opportunity_type")
        batch_op.drop_column("evidence_confidence")
        batch_op.drop_column("source_kind")
