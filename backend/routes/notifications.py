"""
Notifications Router

In-app notifications for the current user. Display text is rendered client-side
from `type` + `actor_name` / `trip_title`; see models/notification.py.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
import structlog

from models.database import get_db
from models.notification import Notification
from models.user import User
from routes.auth import get_current_active_user
from utils.rate_limits import limiter, RateLimits

logger = structlog.get_logger(__name__)
router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    type: str
    trip_id: Optional[int] = None
    actor_name: Optional[str] = None
    trip_title: Optional[str] = None
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    count: int


@router.get("", response_model=List[NotificationResponse])
@limiter.limit(RateLimits.DIARY_LIST)
async def list_notifications(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The current user's notifications, newest first."""
    limit = min(limit, 100)
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/unread-count", response_model=UnreadCountResponse)
@limiter.limit(RateLimits.DIARY_LIST)
async def unread_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Number of unread notifications for the badge."""
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
    )
    return UnreadCountResponse(count=result.scalar() or 0)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
@limiter.limit(RateLimits.DIARY_UPDATE)
async def mark_read(
    request: Request,
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a single notification as read (only the recipient may)."""
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.post("/read-all", response_model=UnreadCountResponse)
@limiter.limit(RateLimits.DIARY_UPDATE)
async def mark_all_read(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all of the current user's notifications as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return UnreadCountResponse(count=0)
