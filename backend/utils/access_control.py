"""
Access Control Utilities

Shared functions for verifying user access to resources.
Prevents IDOR (Insecure Direct Object Reference) vulnerabilities.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from models.trip import Trip
from models.user import User
from models.participant import Participant, PermissionLevel, InvitationStatus

logger = structlog.get_logger(__name__)


async def verify_trip_access(
    trip_id: int,
    current_user: User,
    db: AsyncSession,
    require_edit: bool = False
) -> Trip:
    """
    Verify user has access to a trip.

    Checks:
    1. Trip exists
    2. User is owner OR accepted participant
    3. If require_edit=True, user must have edit permission

    Args:
        trip_id: ID of the trip to check
        current_user: The authenticated user
        db: Database session
        require_edit: If True, user must have editor/owner permission

    Returns:
        Trip object if access granted

    Raises:
        HTTPException 404 if trip not found
        HTTPException 403 if access denied
    """
    # Get trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Check if user is owner
    if trip.owner_id == current_user.id:
        return trip

    # Check if user is an accepted participant
    result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip_id,
            Participant.user_id == current_user.id,
            Participant.invitation_status == InvitationStatus.ACCEPTED.value
        )
    )
    participant = result.scalar_one_or_none()

    if not participant:
        logger.warning(
            "unauthorized_trip_access",
            trip_id=trip_id,
            user_id=current_user.id,
            owner_id=trip.owner_id
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Check edit permission if required
    if require_edit and not participant.can_edit:
        logger.warning(
            "insufficient_permission",
            trip_id=trip_id,
            user_id=current_user.id,
            permission=participant.permission,
            required="editor"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission required"
        )

    return trip


async def verify_diary_entry_access(
    entry,
    current_user: User,
    db: AsyncSession,
    require_author: bool = False
) -> bool:
    """
    Verify user has access to a diary entry.

    Args:
        entry: DiaryEntry object
        current_user: The authenticated user
        db: Database session
        require_author: If True, user must be the author (for edit/delete)

    Returns:
        True if access granted

    Raises:
        HTTPException 403 if access denied
    """
    # If require_author, only the author can access
    if require_author:
        if entry.author_id != current_user.id:
            logger.warning(
                "unauthorized_diary_entry_access",
                entry_id=entry.id,
                user_id=current_user.id,
                author_id=entry.author_id
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return True

    # Otherwise, check trip access
    await verify_trip_access(entry.trip_id, current_user, db, require_edit=False)
    return True
