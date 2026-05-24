"""add_benchmark_thresholds_and_validation

Revision ID: 4e8c43dfca9a
Revises: bbd554023a9d
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4e8c43dfca9a'
down_revision: Union[str, Sequence[str], None] = 'bbd554023a9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'dataset_items',
        sa.Column(
            'required_keywords',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='[]',
            nullable=False,
        ),
    )
    op.add_column(
        'dataset_items',
        sa.Column(
            'required_json_fields',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='[]',
            nullable=False,
        ),
    )
    op.add_column(
        'benchmark_suites',
        sa.Column('semantic_similarity_threshold', sa.Float(), server_default='0.7', nullable=False),
    )
    op.add_column(
        'benchmark_suites',
        sa.Column('keyword_coverage_threshold', sa.Float(), server_default='0.6', nullable=False),
    )
    op.add_column(
        'benchmark_suites',
        sa.Column('json_validity_required', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('benchmark_suites', 'json_validity_required')
    op.drop_column('benchmark_suites', 'keyword_coverage_threshold')
    op.drop_column('benchmark_suites', 'semantic_similarity_threshold')
    op.drop_column('dataset_items', 'required_json_fields')
    op.drop_column('dataset_items', 'required_keywords')
