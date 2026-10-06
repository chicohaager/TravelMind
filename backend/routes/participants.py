"""
Participants Router
Manage trip participants/travelers with photos using SQLite
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from models.database import get_db
from models.participant import Participant
from models.trip import Trip
from models.user import User
from pydantic import BaseModel, Field
from routes.auth import get_current_active_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.images import process_and_save, validate_image
from utils.rate_limits import RateLimits, limiter

logger = structlog.get_logger(__name__)
router = APIRouter()

# Upload configuration
UPLOAD_DIR = Path("./uploads/participants")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


async def verify_trip_access(trip_id: int, current_user: User, db: AsyncSession) -> Trip:
    """Verify user has access to the trip and return the trip object."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.owner_id != current_user.id:
        logger.warning(
            "unauthorized_participant_access", trip_id=trip_id, user_id=current_user.id, owner_id=trip.owner_id
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return trip


# Request/Response Models
class ParticipantCreate(BaseModel):
    name: str = Field(..., example="Max Mustermann")
    email: Optional[str] = Field(None, example="max@example.com")
    role: Optional[str] = Field(None, example="Freund")


class ParticipantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class ParticipantResponse(BaseModel):
    id: int
    trip_id: int
    user_id: Optional[int] = None
    name: str
    email: Optional[str]
    role: Optional[str]
    photo_url: Optional[str]
    permission: Optional[str] = "viewer"
    invitation_status: Optional[str] = "pending"
    invited_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Helper functions


async def save_participant_photo(upload_file: UploadFile, participant_id: int) -> str:
    """Save uploaded participant photo and return the file path"""
    # Read file content
    contents = await upload_file.read()

    # Check file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"Datei zu groß. Maximum: {MAX_FILE_SIZE / (1024*1024)}MB")

    # Validate file type (extension AND mime type)
    if not validate_image(contents, upload_file.filename):
        raise HTTPException(status_code=400, detail=f"Ungültiger Dateityp. Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}")

    # Normalize, auto-orient and compress. Participant photos stay small; no thumbnail needed.
    try:
        processed = await asyncio.to_thread(
            process_and_save, contents, UPLOAD_DIR, "/uploads/participants", make_thumb=False, full_max_edge=512
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Ungültiges Bild: {exc}")

    # Return relative URL path
    return processed.url


# Endpoints
@router.get("/{trip_id}/participants", response_model=List[ParticipantResponse])
@limiter.limit(RateLimits.TRIP_READ)
async def get_participants(
    request: Request,
    trip_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all participants for a trip with pagination.
    Requires authentication and trip ownership.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 500)
    """
    # Enforce maximum limit
    limit = min(limit, 500)

    # Verify access
    await verify_trip_access(trip_id, current_user, db)

    result = await db.execute(
        select(Participant)
        .where(Participant.trip_id == trip_id)
        .order_by(Participant.created_at)
        .offset(skip)
        .limit(limit)
    )
    participants = result.scalars().all()
    return participants


@router.post("/{trip_id}/participants", response_model=ParticipantResponse, status_code=201)
@limiter.limit(RateLimits.TRIP_CREATE)
async def create_participant(
    request: Request,
    trip_id: int,
    participant: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Add a participant to a trip.
    Requires authentication and trip ownership.
    """
    # Verify access
    await verify_trip_access(trip_id, current_user, db)

    new_participant = Participant(
        trip_id=trip_id, name=participant.name, email=participant.email, role=participant.role
    )

    db.add(new_participant)
    await db.commit()
    await db.refresh(new_participant)

    return new_participant


@router.put("/participants/{participant_id}", response_model=ParticipantResponse)
@limiter.limit(RateLimits.TRIP_UPDATE)
async def update_participant(
    request: Request,
    participant_id: int,
    participant: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update participant information.
    Requires authentication and trip ownership.
    """
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    existing_participant = result.scalar_one_or_none()

    if not existing_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Verify trip ownership
    await verify_trip_access(existing_participant.trip_id, current_user, db)

    # Update only provided fields
    update_data = participant.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_participant, field, value)

    existing_participant.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(existing_participant)

    return existing_participant


@router.delete("/participants/{participant_id}", status_code=204)
@limiter.limit(RateLimits.TRIP_DELETE)
async def delete_participant(
    request: Request,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Remove a participant from a trip.
    Requires authentication and trip ownership.
    """
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Verify trip ownership
    await verify_trip_access(participant.trip_id, current_user, db)

    await db.delete(participant)
    await db.commit()

    return None


@router.post("/participants/{participant_id}/upload-photo", response_model=ParticipantResponse)
@limiter.limit(RateLimits.TRIP_CREATE)
async def upload_participant_photo(
    request: Request,
    participant_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a photo for a participant.
    Requires authentication and trip ownership.

    Accepts image files (jpg, jpeg, png, gif, webp) up to 5MB.
    Validates both file extension and MIME type for security.
    """
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Verify trip ownership
    await verify_trip_access(participant.trip_id, current_user, db)

    # Save the uploaded file (with MIME type validation)
    file_url = await save_participant_photo(file, participant_id)

    # Update participant with new photo
    participant.photo_url = file_url
    participant.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participant)

    return participant
