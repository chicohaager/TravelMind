"""
Media Router

Manage individual media items (photos) that belong to diary entries or places.
The media table is the source of truth for photos; see models/media.py.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
import structlog

from models.database import get_db
from models.media import Media
from models.user import User
from routes.auth import get_current_active_user
from utils.access_control import verify_trip_access
from utils.images import delete_upload_file
from utils.rate_limits import limiter, RateLimits

logger = structlog.get_logger(__name__)
router = APIRouter()


class MediaResponse(BaseModel):
    id: int
    url: str
    thumb_url: Optional[str] = None
    caption: Optional[str] = None
    taken_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    order_index: int = 0
    diary_entry_id: Optional[int] = None
    place_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class MediaUpdate(BaseModel):
    caption: Optional[str] = Field(None, max_length=500)


async def _get_media_for_edit(media_id: int, current_user: User, db: AsyncSession) -> Media:
    """Load a media row and verify the user may edit its trip."""
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    # Reuse trip-level access control (owner or editor participant, or superuser).
    await verify_trip_access(media.trip_id, current_user, db, require_edit=True)
    return media


@router.get("/trip/{trip_id}", response_model=List[MediaResponse])
@limiter.limit(RateLimits.DIARY_LIST)
async def get_trip_media(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """All media for a trip (diary + places), newest capture first. Trip-wide gallery."""
    await verify_trip_access(trip_id, current_user, db, require_edit=False)
    result = await db.execute(
        select(Media)
        .where(Media.trip_id == trip_id)
        .order_by(Media.taken_at.desc().nullslast(), Media.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{media_id}", response_model=MediaResponse)
@limiter.limit(RateLimits.DIARY_UPDATE)
async def update_media(
    request: Request,
    media_id: int,
    update: MediaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update editable media metadata (currently the caption)."""
    media = await _get_media_for_edit(media_id, current_user, db)
    if update.caption is not None:
        media.caption = update.caption
    await db.commit()
    await db.refresh(media)
    logger.info("media_updated", media_id=media_id, user_id=current_user.id)
    return media


@router.delete("/{media_id}", status_code=204)
@limiter.limit(RateLimits.DIARY_DELETE)
async def delete_media(
    request: Request,
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a media item and its files (full image + thumbnail)."""
    media = await _get_media_for_edit(media_id, current_user, db)
    url, thumb_url = media.url, media.thumb_url

    await db.delete(media)
    await db.commit()

    delete_upload_file(url)
    if thumb_url and thumb_url != url:
        delete_upload_file(thumb_url)

    logger.info("media_deleted", media_id=media_id, user_id=current_user.id)
    return None
