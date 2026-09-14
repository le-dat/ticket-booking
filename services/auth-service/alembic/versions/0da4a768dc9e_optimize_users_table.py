"""optimize_users_table

Revision ID: 0da4a768dc9e
Revises: a5a497df25e4
Create Date: 2026-09-14 15:59:19.521331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0da4a768dc9e'
down_revision: Union[str, Sequence[str], None] = 'a5a497df25e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.alter_column('users', 'created_at', server_default=sa.text('now()'))
    op.alter_column('users', 'updated_at', server_default=sa.text('now()'))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'updated_at', server_default=None)
    op.alter_column('users', 'created_at', server_default=None)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
