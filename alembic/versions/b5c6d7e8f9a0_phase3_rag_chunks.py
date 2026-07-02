"""Phase 3: RAG chunk tables and match metadata columns.

Revision ID: b5c6d7e8f9a0
Revises: 4a1b2c3d4e5f
Create Date: 2026-07-01 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "4a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "job_chunks" not in tables:
        op.create_table(
            "job_chunks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("chunk_text", sa.Text(), nullable=False),
            sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id", "chunk_index", name="uq_job_chunks_job_index"),
        )
        op.create_index(op.f("ix_job_chunks_job_id"), "job_chunks", ["job_id"], unique=False)

    if "resume_chunks" not in tables:
        op.create_table(
            "resume_chunks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("profile_id", sa.Integer(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("chunk_text", sa.Text(), nullable=False),
            sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "profile_id", "chunk_index", name="uq_resume_chunks_profile_index"
            ),
        )
        op.create_index(
            op.f("ix_resume_chunks_profile_id"), "resume_chunks", ["profile_id"], unique=False
        )

    job_match_columns = {col["name"] for col in inspector.get_columns("job_matches")}
    if "strengths_json" not in job_match_columns:
        op.add_column(
            "job_matches",
            sa.Column("strengths_json", sa.Text(), nullable=False, server_default="[]"),
        )
    if "gaps_json" not in job_match_columns:
        op.add_column(
            "job_matches",
            sa.Column("gaps_json", sa.Text(), nullable=False, server_default="[]"),
        )
    if "evidence_json" not in job_match_columns:
        op.add_column(
            "job_matches",
            sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    job_match_columns = (
        {col["name"] for col in inspector.get_columns("job_matches")}
        if "job_matches" in tables
        else set()
    )
    if "evidence_json" in job_match_columns:
        op.drop_column("job_matches", "evidence_json")
    if "gaps_json" in job_match_columns:
        op.drop_column("job_matches", "gaps_json")
    if "strengths_json" in job_match_columns:
        op.drop_column("job_matches", "strengths_json")

    if "resume_chunks" in tables:
        op.drop_index(op.f("ix_resume_chunks_profile_id"), table_name="resume_chunks")
        op.drop_table("resume_chunks")
    if "job_chunks" in tables:
        op.drop_index(op.f("ix_job_chunks_job_id"), table_name="job_chunks")
        op.drop_table("job_chunks")
