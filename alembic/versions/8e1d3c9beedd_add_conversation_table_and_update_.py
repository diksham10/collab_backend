"""Add conversation table and update messages for group chat

Revision ID: 8e1d3c9beedd
Revises: d4fb1dde29d7
Create Date: 2026-02-25 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8e1d3c9beedd'
down_revision: Union[str, Sequence[str], None] = 'd4fb1dde29d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create conversationtype enum safely
    # PostgreSQL doesn't support IF NOT EXISTS for CREATE TYPE, so we check manually
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'conversationtype') THEN
                CREATE TYPE conversationtype AS ENUM ('DIRECT', 'GROUP');
            END IF;
        END $$;
    """)
    
    # Create messagetype enum safely
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'messagetype') THEN
                CREATE TYPE messagetype AS ENUM ('TEXT', 'IMAGE', 'VIDEO', 'FILE', 'SYSTEM');
            END IF;
        END $$;
    """)
    
    # This migration is being replaced by b1808c7c17f5
    # Mark it as applied but don't do anything
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the enums if they exist
    op.execute("DROP TYPE IF EXISTS messagetype CASCADE")
    op.execute("DROP TYPE IF EXISTS conversationtype CASCADE")
