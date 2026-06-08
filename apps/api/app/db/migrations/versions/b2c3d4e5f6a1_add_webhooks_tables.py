"""add_webhooks_tables

Revision ID: b2c3d4e5f6a1
Revises: a3f8c2e91b4d
Create Date: 2026-06-08 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, Sequence[str], None] = 'a3f8c2e91b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create webhooks and webhook_deliveries tables."""
    op.create_table(
        'webhooks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column(
            'event_types',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='[]',
            nullable=False,
        ),
        sa.Column('secret', sa.String(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('webhook_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column(
            'payload',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Drop webhooks and webhook_deliveries tables."""
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
