"""stub_worktree_migration

This revision was applied to the database by a worktree agent during Phase 5
development but the file was never merged. This stub allows Alembic to resolve
the revision chain. The upgrade is a no-op since the tables already exist.

Revision ID: 8f9e83ef1d00
Revises: 6f875be5cedd
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8f9e83ef1d00'
down_revision: Union[str, Sequence[str], None] = '6f875be5cedd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
