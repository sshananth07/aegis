"""add_prompt_version_id_to_benchmark_suites

Revision ID: 3b1e9d6a4f20
Revises: 00b6d403b57b
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b1e9d6a4f20'
down_revision: Union[str, Sequence[str], None] = '00b6d403b57b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('benchmark_suites', sa.Column('prompt_version_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_benchmark_suites_prompt_version_id_prompt_versions',
        'benchmark_suites',
        'prompt_versions',
        ['prompt_version_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_benchmark_suites_prompt_version_id_prompt_versions',
        'benchmark_suites',
        type_='foreignkey',
    )
    op.drop_column('benchmark_suites', 'prompt_version_id')
