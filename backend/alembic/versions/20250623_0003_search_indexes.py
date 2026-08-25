"""Add GIN full-text search indexes

Revision ID: 0003
Revises: 0002
Create Date: 2025-06-23

Creates GIN indexes on to_tsvector documents for trips, diary entries, places
and media captions, backing the cross-entity search in routes/search.py.
PostgreSQL only.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Keep these in sync with PG_DOCS in routes/search.py.
INDEXES = {
    "ix_trips_fts": (
        "trips",
        "to_tsvector('simple', coalesce(title,'')||' '||coalesce(destination,'')||' '||coalesce(description,''))",
    ),
    "ix_diary_entries_fts": (
        "diary_entries",
        "to_tsvector('simple', coalesce(title,'')||' '||coalesce(content,'')||' '||coalesce(location_name,'')||' '||coalesce(tags::text,''))",
    ),
    "ix_places_fts": (
        "places",
        "to_tsvector('simple', coalesce(name,'')||' '||coalesce(description,'')||' '||coalesce(notes,'')||' '||coalesce(address,'')||' '||coalesce(category,'')||' '||coalesce(tags::text,''))",
    ),
    "ix_media_fts": ("media", "to_tsvector('simple', coalesce(caption,''))"),
}


def upgrade() -> None:
    for name, (table, doc) in INDEXES.items():
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING GIN ({doc})")


def downgrade() -> None:
    for name in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
