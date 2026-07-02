"""add job_parsed nlp boolean columns

Revision ID: 4a1b2c3d4e5f
Revises: 3e2d0541e3a0
Create Date: 2026-07-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "3e2d0541e3a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("job_parsed")}

    if "requires_clearance" not in columns:
        op.add_column(
            "job_parsed",
            sa.Column(
                "requires_clearance",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "sponsorship_mentioned" not in columns:
        op.add_column(
            "job_parsed",
            sa.Column(
                "sponsorship_mentioned",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("job_parsed")}

    if "sponsorship_mentioned" in columns:
        op.drop_column("job_parsed", "sponsorship_mentioned")
    if "requires_clearance" in columns:
        op.drop_column("job_parsed", "requires_clearance")
