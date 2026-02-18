"""add_last_seen_to_users

Revision ID: d4fb1dde29d7
Revises: 7f7046edd5fb
Create Date: 2026-02-18 04:30:50.453695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4fb1dde29d7'
down_revision: Union[str, Sequence[str], None] = '7f7046edd5fb'  # ✅ Changed from None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """Add last_seen column to users table."""
    op.add_column('users', sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove last_seen column from users table."""
    op.drop_column('users', 'last_seen')
