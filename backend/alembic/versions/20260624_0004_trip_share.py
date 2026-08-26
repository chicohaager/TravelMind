"""Add public-sharing columns to trips

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24

Adds is_public (privacy switch) and share_token (unguessable URL slug) to trips,
backing the public read-only diary share links in routes/public.py.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("trips", sa.Column("share_token", sa.String(length=64), nullable=True))
    op.create_index("ix_trips_share_token", "trips", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_trips_share_token", table_name="trips")
    op.drop_column("trips", "share_token")
    op.drop_column("trips", "is_public")
