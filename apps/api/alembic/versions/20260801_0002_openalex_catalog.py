"""openalex catalog

Revision ID: 20260801_0002
Revises: 20260801_0001
Create Date: 2026-08-01 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0002"
down_revision: str | None = "20260801_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add provider identity and paper-specific affiliation metadata."""

    with op.batch_alter_table("institutions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("openalex_id", sa.String(64), nullable=True))
        batch_op.create_unique_constraint(
            batch_op.f("uq_institutions_openalex_id"), ["openalex_id"]
        )

    with op.batch_alter_table("papers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("work_type", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("language", sa.String(8), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_retracted",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )

    with op.batch_alter_table("paper_topics", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("openalex_topic_id", sa.String(64), nullable=True)
        )
        batch_op.add_column(sa.Column("score", sa.Float(), nullable=True))
        batch_op.create_check_constraint(
            batch_op.f("ck_paper_topics_score_range"),
            "score IS NULL OR (score >= 0 AND score <= 1)",
        )
        batch_op.create_unique_constraint(
            batch_op.f("uq_paper_topics_paper_id_openalex_topic_id"),
            ["paper_id", "openalex_topic_id"],
        )

    op.create_table(
        "paper_author_institutions",
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name=op.f("ck_paper_author_institutions_position_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_paper_author_institutions_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["paper_id", "author_id"],
            ["paper_authors.paper_id", "paper_authors.author_id"],
            name=op.f("fk_paper_author_institutions_paper_id_paper_authors"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "paper_id",
            "author_id",
            "institution_id",
            name=op.f("pk_paper_author_institutions"),
        ),
        sa.UniqueConstraint(
            "paper_id",
            "author_id",
            "position",
            name=op.f("uq_paper_author_institutions_paper_id_author_id_position"),
        ),
    )


def downgrade() -> None:
    """Return the academic catalog to the Phase 5 shape."""

    op.drop_table("paper_author_institutions")

    with op.batch_alter_table("paper_topics", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("uq_paper_topics_paper_id_openalex_topic_id"),
            type_="unique",
        )
        batch_op.drop_constraint(
            batch_op.f("ck_paper_topics_score_range"), type_="check"
        )
        batch_op.drop_column("score")
        batch_op.drop_column("openalex_topic_id")

    with op.batch_alter_table("papers", schema=None) as batch_op:
        batch_op.drop_column("is_retracted")
        batch_op.drop_column("language")
        batch_op.drop_column("work_type")

    with op.batch_alter_table("institutions", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("uq_institutions_openalex_id"), type_="unique"
        )
        batch_op.drop_column("openalex_id")
