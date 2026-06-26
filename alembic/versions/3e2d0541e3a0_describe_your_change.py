"""describe your change

Revision ID: 3e2d0541e3a0
Revises: 020f582aa782
Create Date: 2026-06-25 21:42:19.336351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e2d0541e3a0'
down_revision: Union[str, Sequence[str], None] = '020f582aa782'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_parsed",
        sa.Column("requires_clearance", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "job_parsed",
        sa.Column(
            "sponsorship_mentioned",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("job_parsed", "sponsorship_mentioned")
    op.drop_column("job_parsed", "requires_clearance")
