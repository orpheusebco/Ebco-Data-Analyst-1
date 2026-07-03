"""phase3 pinned items (dashboard)

Revision ID: c1a2b3d4e5f6
Revises: f82d6f407669
Create Date: 2026-07-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'f82d6f407669'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pinned_items',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('run_id', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('chart_spec', sa.Text(), nullable=True),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_pinned_items_run_id'), 'pinned_items', ['run_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_pinned_items_run_id'), table_name='pinned_items')
    op.drop_table('pinned_items')
