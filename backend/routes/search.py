"""
Search Router

Cross-entity full-text search over the current user's trips, diary entries,
places and photo captions.

Dialect-aware: on PostgreSQL it uses `to_tsvector`/`websearch_to_tsquery` with
`ts_rank` (the GIN indexes are created in models.database.run_migrations and
Alembic, and share the document expressions defined here). On SQLite (tests /
dev) it falls back to a case-insensitive ILIKE match without ranking.
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request
from models.database import get_db
from models.diary import DiaryEntry
from models.media import Media
from models.place import Place
from models.trip import Trip
from models.user import User
from pydantic import BaseModel
from routes.auth import get_current_active_user
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from utils.rate_limits import limiter

logger = structlog.get_logger(__name__)
router = APIRouter()

LIMIT_PER_TYPE = 10
MIN_QUERY_LEN = 2
SNIPPET_LEN = 160

# PostgreSQL full-text document expressions. These MUST stay in sync with the
# GIN index expressions (see FTS_INDEXES in models/database.py) so the planner
# can use them.
PG_DOCS = {
    "trip": "to_tsvector('simple', coalesce(title,'')||' '||coalesce(destination,'')||' '||coalesce(description,''))",
    "diary": "to_tsvector('simple', coalesce(title,'')||' '||coalesce(content,'')||' '||coalesce(location_name,'')||' '||coalesce(tags::text,''))",  # noqa: E501
    "place": "to_tsvector('simple', coalesce(name,'')||' '||coalesce(description,'')||' '||coalesce(notes,'')||' '||coalesce(address,'')||' '||coalesce(category,'')||' '||coalesce(tags::text,''))",  # noqa: E501
    "media": "to_tsvector('simple', coalesce(caption,''))",
}

# Per-entity PostgreSQL queries: each selects the common columns id, trip_id,
# title, snippet plus a rank. ``:uid`` and ``:q`` are bound parameters.
PG_QUERIES = {
    "trip": f"""
        SELECT id, id AS trip_id, title, description AS snippet,
               ts_rank({PG_DOCS['trip']}, websearch_to_tsquery('simple', :q)) AS rank
        FROM trips
        WHERE owner_id = :uid AND {PG_DOCS['trip']} @@ websearch_to_tsquery('simple', :q)
        ORDER BY rank DESC LIMIT :limit
    """,
    "diary": f"""
        SELECT id, trip_id, title, content AS snippet,
               ts_rank({PG_DOCS['diary']}, websearch_to_tsquery('simple', :q)) AS rank
        FROM diary_entries
        WHERE author_id = :uid AND {PG_DOCS['diary']} @@ websearch_to_tsquery('simple', :q)
        ORDER BY rank DESC LIMIT :limit
    """,
    "place": f"""
        SELECT id, trip_id, name AS title, coalesce(description, notes) AS snippet,
               ts_rank({PG_DOCS['place']}, websearch_to_tsquery('simple', :q)) AS rank
        FROM places
        WHERE trip_id IN (SELECT id FROM trips WHERE owner_id = :uid)
          AND {PG_DOCS['place']} @@ websearch_to_tsquery('simple', :q)
        ORDER BY rank DESC LIMIT :limit
    """,
    "media": f"""
        SELECT id, trip_id, caption AS title, NULL AS snippet,
               ts_rank({PG_DOCS['media']}, websearch_to_tsquery('simple', :q)) AS rank
        FROM media
        WHERE owner_id = :uid AND caption IS NOT NULL
          AND {PG_DOCS['media']} @@ websearch_to_tsquery('simple', :q)
        ORDER BY rank DESC LIMIT :limit
    """,
}


class SearchHit(BaseModel):
    type: str  # trip | diary | place | media
    id: int
    trip_id: Optional[int] = None
    title: Optional[str] = None
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchHit]


def _snippet(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = " ".join(value.split())
    return value[:SNIPPET_LEN] + ("…" if len(value) > SNIPPET_LEN else "")


async def _search_pg(db: AsyncSession, uid: int, q: str) -> List[SearchHit]:
    hits: List[SearchHit] = []
    for kind, sql in PG_QUERIES.items():
        result = await db.execute(text(sql), {"q": q, "uid": uid, "limit": LIMIT_PER_TYPE})
        for row in result.mappings().all():
            hits.append(
                SearchHit(
                    type=kind,
                    id=row["id"],
                    trip_id=row["trip_id"],
                    title=row["title"],
                    snippet=_snippet(row["snippet"]),
                )
            )
    return hits


async def _search_sqlite(db: AsyncSession, uid: int, q: str) -> List[SearchHit]:
    """Fallback substring search (no ranking) for SQLite/dev and tests."""
    like = f"%{q.lower()}%"

    def cond(*cols):
        return or_(*[func.lower(func.coalesce(c, "")).like(like) for c in cols])

    hits: List[SearchHit] = []

    trips = (
        (
            await db.execute(
                select(Trip)
                .where(Trip.owner_id == uid, cond(Trip.title, Trip.destination, Trip.description))
                .limit(LIMIT_PER_TYPE)
            )
        )
        .scalars()
        .all()
    )
    hits += [
        SearchHit(type="trip", id=t.id, trip_id=t.id, title=t.title, snippet=_snippet(t.description)) for t in trips
    ]

    entries = (
        (
            await db.execute(
                select(DiaryEntry)
                .where(
                    DiaryEntry.author_id == uid,
                    cond(DiaryEntry.title, DiaryEntry.content, DiaryEntry.location_name),
                )
                .limit(LIMIT_PER_TYPE)
            )
        )
        .scalars()
        .all()
    )
    hits += [
        SearchHit(type="diary", id=e.id, trip_id=e.trip_id, title=e.title, snippet=_snippet(e.content)) for e in entries
    ]

    owned = select(Trip.id).where(Trip.owner_id == uid)
    places = (
        (
            await db.execute(
                select(Place)
                .where(
                    Place.trip_id.in_(owned),
                    cond(Place.name, Place.description, Place.notes, Place.address, Place.category),
                )
                .limit(LIMIT_PER_TYPE)
            )
        )
        .scalars()
        .all()
    )
    hits += [
        SearchHit(type="place", id=p.id, trip_id=p.trip_id, title=p.name, snippet=_snippet(p.description or p.notes))
        for p in places
    ]

    media = (
        (await db.execute(select(Media).where(Media.owner_id == uid, cond(Media.caption)).limit(LIMIT_PER_TYPE)))
        .scalars()
        .all()
    )
    hits += [SearchHit(type="media", id=m.id, trip_id=m.trip_id, title=m.caption, snippet=None) for m in media]

    return hits


@router.get("", response_model=SearchResponse)
@router.get("/", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str = Query(..., description="Search query"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search the current user's trips, diary entries, places and photo captions."""
    q = (q or "").strip()
    if len(q) < MIN_QUERY_LEN:
        return SearchResponse(query=q, total=0, results=[])

    dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
    if dialect == "postgresql":
        hits = await _search_pg(db, current_user.id, q)
    else:
        hits = await _search_sqlite(db, current_user.id, q)

    logger.info("search_performed", user_id=current_user.id, query=q, hits=len(hits), dialect=dialect)
    return SearchResponse(query=q, total=len(hits), results=hits)
