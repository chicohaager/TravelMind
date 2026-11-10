"""
Notification service

Helper for raising in-app notifications. The caller is responsible for committing
the surrounding transaction (notifications are created alongside the event that
triggers them, e.g. a trip invitation).
"""

from typing import Optional

from models.notification import Notification
from sqlalchemy.ext.asyncio import AsyncSession

# Known notification types.
INVITE_RECEIVED = "invite_received"
INVITE_ACCEPTED = "invite_accepted"
INVITE_DECLINED = "invite_declined"


def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    type: str,
    trip_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    trip_title: Optional[str] = None,
) -> Notification:
    """Add a notification to the session (does not commit)."""
    notification = Notification(
        user_id=user_id,
        type=type,
        trip_id=trip_id,
        actor_name=actor_name,
        trip_title=trip_title,
    )
    db.add(notification)
    return notification
