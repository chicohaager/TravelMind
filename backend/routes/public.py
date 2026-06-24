"""Public (unauthenticated) read-only access to shared trip diaries.

A trip owner can publish their diary via PATCH /api/trips/{id}/share, which sets
is_public and mints an unguessable share_token. The diary is then reachable here
WITHOUT authentication at /api/public/diary/{token}.

The payload is intentionally minimal (data-sparsam): trip header + diary entries
with photos only. No owner/user data, budget, participants, places, or GPS.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
import structlog

from models.database import get_db
from models.trip import Trip
from models.diary import DiaryEntry
from utils.rate_limits import limiter, RateLimits

logger = structlog.get_logger(__name__)
router = APIRouter()


class PublicMedia(BaseModel):
    id: int
    url: str
    thumb_url: Optional[str] = None
    caption: Optional[str] = None
    taken_at: Optional[datetime] = None
    width: Optional[int] = None
    height: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PublicDiaryEntry(BaseModel):
    title: str
    content: str
    entry_date: Optional[datetime] = None
    location_name: Optional[str] = None
    mood: Optional[str] = None
    rating: Optional[int] = None
    media: List[PublicMedia] = []

    model_config = ConfigDict(from_attributes=True)


class PublicDiary(BaseModel):
    title: str
    destination: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    cover_image: Optional[str] = None
    entries: List[PublicDiaryEntry] = []


@router.get("/diary/{token}", response_model=PublicDiary)
@limiter.limit(RateLimits.PUBLIC_STATUS)
async def get_public_diary(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a publicly shared trip diary by its share token. No auth required."""
    result = await db.execute(
        select(Trip).where(Trip.share_token == token, Trip.is_public.is_(True))
    )
    trip = result.scalar_one_or_none()
    # A missing token and a disabled/non-existent share are indistinguishable on
    # purpose, so a revoked link reveals nothing.
    if not trip:
        raise HTTPException(status_code=404, detail="Not found")

    entries_result = await db.execute(
        select(DiaryEntry)
        .options(selectinload(DiaryEntry.media))
        .where(DiaryEntry.trip_id == trip.id)
        .order_by(DiaryEntry.entry_date.desc())
    )
    entries = entries_result.scalars().all()

    logger.info("public_diary_viewed", trip_id=trip.id, entries=len(entries))

    return PublicDiary(
        title=trip.title,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        cover_image=trip.cover_image,
        entries=entries,
    )
