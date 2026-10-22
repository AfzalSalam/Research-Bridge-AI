"""Owner-scoped generation consent and conservative call reservations."""

import sqlalchemy as sa

from alembic import op

revision = "20261021_0012"
down_revision = "20261017_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "answer_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("account_owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("reserved_calls", sa.Integer(), nullable=False),
        sa.Column("disclosure_version", sa.String(60), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "request_id"),
    )
    op.create_index(
        "ix_answer_reservations_owner_day", "answer_reservations", ["owner_id", "day"]
    )


def downgrade():
    op.drop_table("answer_reservations")
