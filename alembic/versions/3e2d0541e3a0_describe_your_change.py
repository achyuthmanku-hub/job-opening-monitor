"""add job_parsed clearance and sponsorship columns

Revision ID: 3e2d0541e3a0
Revises: 020f582aa782
Create Date: 2026-06-25 21:42:19.336351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3e2d0541e3a0"
down_revision: Union[str, Sequence[str], None] = "020f582aa782"
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
