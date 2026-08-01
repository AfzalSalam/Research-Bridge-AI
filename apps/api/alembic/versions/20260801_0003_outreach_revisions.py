"""evidence-grounded outreach revisions

Revision ID: 20260801_0003
Revises: 20260801_0002
Create Date: 2026-08-01 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0003"
down_revision: str | None = "20260801_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add grounding metadata and immutable draft revisions."""

    with op.batch_alter_table("outreach_drafts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("claim_evidence", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("evidence_map_status", sa.String(length=40), nullable=True)
        )
        batch_op.add_column(
            sa.Column("fallback_reason", sa.String(length=80), nullable=True)
        )
        batch_op.add_column(
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.execute(
        sa.text(
            "UPDATE outreach_drafts "
            "SET claim_evidence = '[]', evidence_map_status = "
            "'manual-edit-needs-review'"
        )
    )

    with op.batch_alter_table("outreach_drafts", schema=None) as batch_op:
        batch_op.alter_column("claim_evidence", existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column(
            "evidence_map_status", existing_type=sa.String(length=40), nullable=False
        )

    op.create_table(
        "outreach_draft_revisions",
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("editor_owner_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("claim_evidence", sa.JSON(), nullable=False),
        sa.Column("evidence_map_status", sa.String(length=40), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version >= 1",
            name=op.f("ck_outreach_draft_revisions_version_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["outreach_drafts.id"],
            name=op.f("fk_outreach_draft_revisions_draft_id_outreach_drafts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["editor_owner_id"],
            ["account_owners.id"],
            name=op.f("fk_outreach_draft_revisions_editor_owner_id_account_owners"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outreach_draft_revisions")),
        sa.UniqueConstraint(
            "draft_id",
            "version",
            name=op.f("uq_outreach_draft_revisions_draft_id_version"),
        ),
    )
    with op.batch_alter_table("outreach_draft_revisions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_outreach_draft_revisions_draft_id"),
            ["draft_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove live outreach revision support."""

    with op.batch_alter_table("outreach_draft_revisions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_outreach_draft_revisions_draft_id"))
    op.drop_table("outreach_draft_revisions")

    with op.batch_alter_table("outreach_drafts", schema=None) as batch_op:
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("fallback_reason")
        batch_op.drop_column("evidence_map_status")
        batch_op.drop_column("claim_evidence")
