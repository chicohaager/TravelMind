"""Add media table and backfill from legacy photos arrays

Revision ID: 0002
Revises: 0001
Create Date: 2025-06-23

Introduces the `media` table as the source of truth for diary/place photos
(caption, capture time, GPS, dimensions, ordering) and backfills it from the
legacy `photos` JSON arrays on diary_entries and places.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_THUMB_EXPR = (
    "CASE WHEN elem.value LIKE '%.webp' "
    "THEN regexp_replace(elem.value, '\\.webp$', '_thumb.webp') "
    "ELSE elem.value END"
)


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("diary_entry_id", sa.Integer(), nullable=True),
        sa.Column("place_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("thumb_url", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=50), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("taken_at", sa.DateTime(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diary_entry_id"], ["diary_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_id"), "media", ["id"], unique=False)
    op.create_index(op.f("ix_media_owner_id"), "media", ["owner_id"], unique=False)
    op.create_index(op.f("ix_media_trip_id"), "media", ["trip_id"], unique=False)
    op.create_index(op.f("ix_media_diary_entry_id"), "media", ["diary_entry_id"], unique=False)
    op.create_index(op.f("ix_media_place_id"), "media", ["place_id"], unique=False)

    # Backfill from legacy photos arrays (idempotent via NOT EXISTS guard).
    op.execute(f"""
        INSERT INTO media (owner_id, trip_id, diary_entry_id, url, thumb_url, order_index, created_at)
        SELECT d.author_id, d.trip_id, d.id, elem.value, {_THUMB_EXPR}, (elem.ord - 1)::int, now()
        FROM diary_entries d
        CROSS JOIN LATERAL jsonb_array_elements_text(d.photos::jsonb)
             WITH ORDINALITY AS elem(value, ord)
        WHERE d.photos IS NOT NULL
          AND jsonb_typeof(d.photos::jsonb) = 'array'
          AND jsonb_array_length(d.photos::jsonb) > 0
          AND NOT EXISTS (SELECT 1 FROM media m WHERE m.diary_entry_id = d.id)
    """)
    op.execute(f"""
        INSERT INTO media (owner_id, trip_id, place_id, url, thumb_url, order_index, created_at)
        SELECT t.owner_id, p.trip_id, p.id, elem.value, {_THUMB_EXPR}, (elem.ord - 1)::int, now()
        FROM places p
        JOIN trips t ON t.id = p.trip_id
        CROSS JOIN LATERAL jsonb_array_elements_text(p.photos::jsonb)
             WITH ORDINALITY AS elem(value, ord)
        WHERE p.photos IS NOT NULL
          AND jsonb_typeof(p.photos::jsonb) = 'array'
          AND jsonb_array_length(p.photos::jsonb) > 0
          AND NOT EXISTS (SELECT 1 FROM media m WHERE m.place_id = p.id)
    """)


def downgrade() -> None:
    op.drop_index(op.f("ix_media_place_id"), table_name="media")
    op.drop_index(op.f("ix_media_diary_entry_id"), table_name="media")
    op.drop_index(op.f("ix_media_trip_id"), table_name="media")
    op.drop_index(op.f("ix_media_owner_id"), table_name="media")
    op.drop_index(op.f("ix_media_id"), table_name="media")
    op.drop_table("media")
