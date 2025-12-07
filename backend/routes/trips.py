"""
Trips Router
CRUD operations for trips with SQLite persistence
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import os
import uuid
import magic
from pathlib import Path
from services.geocoding import geocoding_service
from utils.rate_limits import limiter, RateLimits
from models.database import get_db
from models.trip import Trip
from models.user import User
from models.place import Place
from models.diary import DiaryEntry
from models.expense import Expense
from models.participant import Participant, PermissionLevel, InvitationStatus
from routes.auth import get_current_user, get_optional_user, get_current_active_user
from services.audit_service import audit_service
from sqlalchemy import or_
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

# Upload configuration
UPLOAD_DIR = Path("./uploads/trips")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Demo mode configuration
ENABLE_DEMO_MODE = os.getenv("ENABLE_DEMO_MODE", "false").lower() == "true"


# Request/Response Models
class TripCreate(BaseModel):
    title: str = Field(..., example="Sommer in Portugal")
    destination: str = Field(..., example="Lissabon")
    description: Optional[str] = Field(None, example="Eine entspannte Reise...")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    interests: List[str] = Field(default=[], example=["culture", "food"])
    budget: Optional[float] = Field(None, example=1500.0)
    currency: str = Field(default="EUR", example="EUR")


class TripUpdate(BaseModel):
    title: Optional[str] = Field(None, example="Portugal Abenteuer")
    destination: Optional[str] = Field(None, example="Porto")
    description: Optional[str] = Field(None, example="Aktualisierte Beschreibung...")
    start_date: Optional[datetime] = Field(None, example="2025-07-15T00:00:00Z")
    end_date: Optional[datetime] = Field(None, example="2025-07-22T00:00:00Z")
    latitude: Optional[float] = Field(None, example=41.1579)
    longitude: Optional[float] = Field(None, example=-8.6291)
    interests: Optional[List[str]] = Field(None, example=["wine", "architecture"])
    budget: Optional[float] = Field(None, example=2000.0)
    currency: Optional[str] = Field(None, example="EUR")
    cover_image: Optional[str] = Field(None, example="/uploads/trips/1_newimage.jpg")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Portugal Abenteuer",
                "budget": 2000.0,
                "interests": ["wine", "architecture", "history"]
            }
        }


class TripResponse(BaseModel):
    id: int = Field(..., example=1)
    title: str = Field(..., example="Sommer in Portugal")
    destination: str = Field(..., example="Lissabon")
    description: Optional[str] = Field(None, example="Eine entspannte Reise durch die Hauptstadt Portugals...")
    start_date: Optional[datetime] = Field(None, example="2025-07-15T00:00:00Z")
    end_date: Optional[datetime] = Field(None, example="2025-07-22T00:00:00Z")
    latitude: Optional[float] = Field(None, example=38.7223)
    longitude: Optional[float] = Field(None, example=-9.1393)
    interests: List[str] = Field(default=[], example=["culture", "food", "photography"])
    budget: Optional[float] = Field(None, example=1500.0)
    currency: str = Field(default="EUR", example="EUR")
    cover_image: Optional[str] = Field(None, example="/uploads/trips/1_abc123.jpg")
    created_at: datetime = Field(..., example="2025-01-15T10:30:00Z")
    updated_at: Optional[datetime] = Field(None, example="2025-01-16T14:45:00Z")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Sommer in Portugal",
                "destination": "Lissabon",
                "description": "Eine entspannte Reise durch die Hauptstadt Portugals...",
                "start_date": "2025-07-15T00:00:00Z",
                "end_date": "2025-07-22T00:00:00Z",
                "latitude": 38.7223,
                "longitude": -9.1393,
                "interests": ["culture", "food", "photography"],
                "budget": 1500.0,
                "currency": "EUR",
                "cover_image": "/uploads/trips/1_abc123.jpg",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-16T14:45:00Z"
            }
        }


# Helper functions
def validate_file_type(contents: bytes, filename: str) -> bool:
    """
    Validate file type by checking actual content, not just extension.
    Uses python-magic to detect MIME type from file content.
    """
    # Check extension first
    extension = filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False

    # Check actual MIME type using python-magic
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(contents)

    return mime_type in ALLOWED_MIME_TYPES


async def save_upload_file(upload_file: UploadFile, trip_id: int) -> str:
    """
    Save uploaded file and return the file path.
    Validates both extension and actual file content for security.
    """
    # Read file content
    contents = await upload_file.read()

    # Check file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximum: {MAX_FILE_SIZE / (1024*1024)}MB"
        )

    # Validate file type by content (security check)
    if not validate_file_type(contents, upload_file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Dateityp. Nur Bilder erlaubt: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    extension = upload_file.filename.split(".")[-1].lower()
    unique_filename = f"{trip_id}_{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info("file_uploaded", trip_id=trip_id, filename=unique_filename, size=len(contents))

    # Return relative URL path
    return f"/uploads/trips/{unique_filename}"


async def get_or_create_demo_user(db: AsyncSession) -> Optional[User]:
    """
    Get or create demo user for trips (only if demo mode is enabled).
    Returns None if demo mode is disabled.
    """
    if not ENABLE_DEMO_MODE:
        return None

    result = await db.execute(select(User).where(User.username == "demo"))
    user = result.scalar_one_or_none()

    if not user:
        # Get demo password from environment or use a random one
        demo_password = os.getenv("DEMO_PASSWORD")
        if not demo_password:
            logger.warning("Demo mode enabled but no DEMO_PASSWORD set. Demo user will not be created.")
            return None

        user = User(
            username="demo",
            email="demo@travelmind.local",
            hashed_password=User.hash_password(demo_password),
            full_name="Demo User",
            is_active=True
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            logger.info("demo_user_created", user_id=user.id)
        except Exception as e:
            await db.rollback()
            logger.error("demo_user_creation_failed", error=str(e))
            return None

    return user


async def check_trip_access(
    trip: Trip,
    user: User,
    db: AsyncSession,
    require_edit: bool = False
) -> Optional[str]:
    """
    Check if user has access to the trip.
    Returns the permission level if access is granted, None otherwise.

    Args:
        trip: The trip to check access for
        user: The user requesting access
        db: Database session
        require_edit: If True, requires edit permission (owner/editor)

    Returns:
        Permission level string or None
    """
    # Admin has full access to all trips
    if user.is_superuser:
        return PermissionLevel.OWNER.value

    # Owner has full access
    if trip.owner_id == user.id:
        return PermissionLevel.OWNER.value

    # Check if user is a participant with accepted invitation
    result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip.id,
            Participant.user_id == user.id,
            Participant.invitation_status == InvitationStatus.ACCEPTED.value
        )
    )
    participant = result.scalar_one_or_none()

    if participant:
        if require_edit and participant.permission == PermissionLevel.VIEWER.value:
            return None
        return participant.permission

    return None


async def verify_trip_access(
    trip: Trip,
    user: User,
    db: AsyncSession,
    require_edit: bool = False
) -> str:
    """
    Verify that the user has access to the trip.
    Raises HTTPException if access check fails.
    Returns the permission level.
    """
    permission = await check_trip_access(trip, user, db, require_edit)

    if permission is None:
        logger.warning(
            "unauthorized_trip_access",
            trip_id=trip.id,
            user_id=user.id,
            owner_id=trip.owner_id,
            require_edit=require_edit
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this trip"
        )

    return permission


async def verify_trip_ownership(trip: Trip, user: User, db: AsyncSession = None) -> None:
    """
    Verify that the user owns the trip (or is admin).
    Raises HTTPException if ownership check fails.
    """
    # Admin can do anything
    if user.is_superuser:
        return

    if trip.owner_id != user.id:
        logger.warning("unauthorized_trip_access", trip_id=trip.id, user_id=user.id, owner_id=trip.owner_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this trip"
        )


# Endpoints
@router.get("", response_model=List[TripResponse])
@router.get("/", response_model=List[TripResponse])
@limiter.limit(RateLimits.TRIP_LIST)
async def get_trips(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all trips for current user with pagination.

    Returns list of trips with basic information.
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 500)
    """
    # Enforce maximum limit
    limit = min(limit, 500)

    if current_user:
        # Admin sees all trips
        if current_user.is_superuser:
            query = (
                select(Trip)
                .options(selectinload(Trip.places))
                .order_by(Trip.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(query)
            trips = result.scalars().all()
            logger.info("admin_trips_fetched", user_id=current_user.id, count=len(trips))
        else:
            # Get trip IDs where user is participant with accepted status
            participant_query = (
                select(Participant.trip_id)
                .where(
                    Participant.user_id == current_user.id,
                    Participant.invitation_status == InvitationStatus.ACCEPTED.value
                )
            )
            participant_result = await db.execute(participant_query)
            shared_trip_ids = [row[0] for row in participant_result.fetchall()]

            # Return user's own trips + shared trips
            query = (
                select(Trip)
                .options(selectinload(Trip.places))
                .where(
                    or_(
                        Trip.owner_id == current_user.id,
                        Trip.id.in_(shared_trip_ids) if shared_trip_ids else False
                    )
                )
                .order_by(Trip.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(query)
            trips = result.scalars().all()
            logger.info("trips_fetched", user_id=current_user.id, count=len(trips), shared=len(shared_trip_ids))
    else:
        # Return demo trips if demo mode enabled
        if not ENABLE_DEMO_MODE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Demo mode is disabled."
            )
        query = (
            select(Trip)
            .options(selectinload(Trip.places))
            .order_by(Trip.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        trips = result.scalars().all()
    return trips


@router.get("/invitations/pending", response_model=List[dict])
@limiter.limit(RateLimits.TRIP_LIST)
async def get_pending_invitations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all pending trip invitations for the current user.

    Returns list of trips the user has been invited to but hasn't responded yet.
    """
    # Get pending invitations
    result = await db.execute(
        select(Participant, Trip)
        .join(Trip, Participant.trip_id == Trip.id)
        .where(
            Participant.user_id == current_user.id,
            Participant.invitation_status == InvitationStatus.PENDING.value
        )
        .order_by(Participant.created_at.desc())
    )
    rows = result.all()

    invitations = []
    for participant, trip in rows:
        # Get owner info
        owner_result = await db.execute(
            select(User).where(User.id == trip.owner_id)
        )
        owner = owner_result.scalar_one_or_none()

        invitations.append({
            "participant_id": participant.id,
            "trip_id": trip.id,
            "trip_title": trip.title,
            "trip_destination": trip.destination,
            "trip_cover_image": trip.cover_image,
            "permission": participant.permission,
            "invited_at": participant.invited_at,
            "invited_by": owner.username if owner else "Unknown"
        })

    return invitations


@router.get("/{trip_id}", response_model=TripResponse)
@limiter.limit(RateLimits.TRIP_READ)
async def get_trip(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get a specific trip by ID with eager-loaded relationships.

    Returns detailed information about a single trip including places.
    Access is granted if user is owner, participant, or admin.
    """
    query = select(Trip).options(
        selectinload(Trip.places),
        selectinload(Trip.diary_entries),
    ).where(Trip.id == trip_id)

    result = await db.execute(query)
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # If user is authenticated, verify access (owner, participant, or admin)
    if current_user:
        await verify_trip_access(trip, current_user, db, require_edit=False)
    elif not ENABLE_DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return trip


@router.post("", response_model=TripResponse, status_code=201)
@router.post("/", response_model=TripResponse, status_code=201)
@limiter.limit(RateLimits.TRIP_CREATE)
async def create_trip(
    request: Request,
    trip: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Create a new trip.

    Creates a new trip with the provided information.
    Requires authentication unless demo mode is enabled.
    """
    # Determine user
    if current_user:
        user = current_user
    else:
        # Try demo mode
        user = await get_or_create_demo_user(db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Demo mode is disabled or not configured."
            )

    new_trip = Trip(
        title=trip.title,
        destination=trip.destination,
        description=trip.description,
        start_date=trip.start_date,
        end_date=trip.end_date,
        latitude=trip.latitude,
        longitude=trip.longitude,
        interests=trip.interests,
        budget=trip.budget,
        currency=trip.currency,
        owner_id=user.id
    )

    db.add(new_trip)
    await db.commit()
    await db.refresh(new_trip)

    logger.info("trip_created", trip_id=new_trip.id, user_id=user.id, destination=new_trip.destination)

    # Audit log: trip creation
    await audit_service.log_data_event(
        db=db,
        action="create",
        resource_type="trip",
        resource_id=new_trip.id,
        user_id=user.id,
        username=user.username,
        request=request,
        details={"destination": new_trip.destination, "title": new_trip.title}
    )

    return new_trip


@router.put("/{trip_id}", response_model=TripResponse)
@limiter.limit(RateLimits.TRIP_UPDATE)
async def update_trip(
    request: Request,
    trip_id: int,
    trip: TripUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing trip.

    Updates trip information. Only provided fields will be updated.
    Requires authentication and ownership.
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    existing_trip = result.scalar_one_or_none()

    if not existing_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    await verify_trip_ownership(existing_trip, current_user)

    # Update only provided fields
    update_data = trip.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_trip, field, value)

    existing_trip.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(existing_trip)

    logger.info("trip_updated", trip_id=trip_id, user_id=current_user.id)

    # Audit log: trip update
    await audit_service.log_data_event(
        db=db,
        action="update",
        resource_type="trip",
        resource_id=trip_id,
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details={"updated_fields": list(update_data.keys())}
    )

    return existing_trip


@router.delete("/{trip_id}", status_code=204)
@limiter.limit(RateLimits.TRIP_DELETE)
async def delete_trip(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a trip.

    Permanently deletes a trip and all associated data.
    Requires authentication and ownership.
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    await verify_trip_ownership(trip, current_user)

    # Store trip info for audit before deletion
    trip_title = trip.title
    trip_destination = trip.destination

    await db.delete(trip)
    await db.commit()

    logger.info("trip_deleted", trip_id=trip_id, user_id=current_user.id)

    # Audit log: trip deletion
    await audit_service.log_data_event(
        db=db,
        action="delete",
        resource_type="trip",
        resource_id=trip_id,
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details={"title": trip_title, "destination": trip_destination}
    )

    return None


@router.post("/{trip_id}/upload-image", response_model=TripResponse)
@limiter.limit(RateLimits.TRIP_UPLOAD)
async def upload_trip_image(
    request: Request,
    trip_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a cover image for a trip.

    Accepts image files (jpg, jpeg, png, gif, webp) up to 10MB.
    Validates file content for security.
    Updates the trip's cover_image field with the uploaded file URL.
    Requires authentication and ownership.
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    await verify_trip_ownership(trip, current_user)

    # Save the uploaded file (with content validation)
    file_url = await save_upload_file(file, trip_id)

    # Update trip with new cover image
    trip.cover_image = file_url
    trip.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(trip)

    return trip


@router.get("/{trip_id}/summary")
@limiter.limit(RateLimits.TRIP_READ)
async def get_trip_summary(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get trip summary with statistics.

    Returns overview statistics like total places, diary entries,
    total cost, duration, etc.
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership if authenticated
    if current_user and trip.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this trip"
        )

    # Count places
    places_result = await db.execute(
        select(func.count(Place.id)).where(Place.trip_id == trip_id)
    )
    total_places = places_result.scalar() or 0

    # Count diary entries
    diary_result = await db.execute(
        select(func.count(DiaryEntry.id)).where(DiaryEntry.trip_id == trip_id)
    )
    total_diary_entries = diary_result.scalar() or 0

    # Calculate total expenses
    expenses_result = await db.execute(
        select(func.sum(Expense.amount)).where(Expense.trip_id == trip_id)
    )
    total_cost = expenses_result.scalar() or 0.0

    # Calculate duration in days
    days_count = 0
    if trip.start_date and trip.end_date:
        delta = trip.end_date - trip.start_date
        days_count = delta.days + 1

    return {
        "trip_id": trip_id,
        "total_places": total_places,
        "total_diary_entries": total_diary_entries,
        "total_cost": total_cost,
        "currency": trip.currency,
        "days_count": days_count,
        "budget": trip.budget,
        "budget_remaining": (trip.budget - total_cost) if trip.budget else None
    }


@router.get("/geocode/{location}")
@limiter.limit(RateLimits.GEOCODE)
async def geocode_location(request: Request, location: str):
    """
    Get coordinates for a location name.

    Converts a location name (e.g., "Barcelona", "Rome, Italy") to
    latitude and longitude coordinates using OpenStreetMap Nominatim.
    """
    result = await geocoding_service.geocode(location)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Koordinaten für '{location}' nicht gefunden"
        )

    logger.info("location_geocoded", location=location, success=True)

    return result


# ============================================================
# Trip Sharing / Invitation Endpoints
# ============================================================

class ShareTripRequest(BaseModel):
    """Request body for sharing a trip"""
    username_or_email: str = Field(..., description="Username or email of user to invite")
    permission: str = Field(default="viewer", description="Permission level: viewer, editor")


class ShareParticipantResponse(BaseModel):
    """Response model for participant in sharing context"""
    id: int
    trip_id: int
    user_id: Optional[int]
    name: str
    email: Optional[str]
    role: Optional[str]
    permission: str
    invitation_status: str
    invited_at: Optional[datetime]
    accepted_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("/{trip_id}/share", response_model=ShareParticipantResponse, status_code=201)
@limiter.limit(RateLimits.TRIP_CREATE)
async def share_trip(
    request: Request,
    trip_id: int,
    share_request: ShareTripRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Invite a user to a trip.

    Creates an invitation for another user to join the trip.
    Only owner or admin can invite others.
    """
    # Get trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Only owner or admin can share
    await verify_trip_ownership(trip, current_user)

    # Validate permission level
    if share_request.permission not in [PermissionLevel.EDITOR.value, PermissionLevel.VIEWER.value]:
        raise HTTPException(
            status_code=400,
            detail="Invalid permission level. Use 'editor' or 'viewer'."
        )

    # Find user by username or email
    result = await db.execute(
        select(User).where(
            or_(
                User.username == share_request.username_or_email,
                User.email == share_request.username_or_email
            )
        )
    )
    invited_user = result.scalar_one_or_none()

    if not invited_user:
        raise HTTPException(
            status_code=404,
            detail="User not found. Please check the username or email."
        )

    # Cannot invite yourself
    if invited_user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot invite yourself to your own trip."
        )

    # Check if user is already a participant
    result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip_id,
            Participant.user_id == invited_user.id
        )
    )
    existing_participant = result.scalar_one_or_none()

    if existing_participant:
        raise HTTPException(
            status_code=400,
            detail="User is already invited to this trip."
        )

    # Create participant invitation
    participant = Participant(
        trip_id=trip_id,
        user_id=invited_user.id,
        name=invited_user.full_name or invited_user.username,
        email=invited_user.email,
        permission=share_request.permission,
        invitation_status=InvitationStatus.PENDING.value
    )

    db.add(participant)
    await db.commit()
    await db.refresh(participant)

    logger.info(
        "trip_shared",
        trip_id=trip_id,
        inviter_id=current_user.id,
        invited_user_id=invited_user.id,
        permission=share_request.permission
    )

    # Audit log
    await audit_service.log_data_event(
        db=db,
        action="share",
        resource_type="trip",
        resource_id=trip_id,
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details={
            "invited_user": invited_user.username,
            "permission": share_request.permission
        }
    )

    return participant


@router.post("/{trip_id}/share/accept")
@limiter.limit(RateLimits.TRIP_UPDATE)
async def accept_trip_invitation(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accept an invitation to a trip.

    Changes invitation status from pending to accepted.
    """
    # Find participant record for current user
    result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip_id,
            Participant.user_id == current_user.id
        )
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=404,
            detail="No invitation found for this trip."
        )

    if participant.invitation_status == InvitationStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=400,
            detail="Invitation already accepted."
        )

    if participant.invitation_status == InvitationStatus.DECLINED.value:
        raise HTTPException(
            status_code=400,
            detail="Invitation was already declined. Contact the trip owner for a new invitation."
        )

    # Accept invitation
    participant.invitation_status = InvitationStatus.ACCEPTED.value
    participant.accepted_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(
        "trip_invitation_accepted",
        trip_id=trip_id,
        user_id=current_user.id
    )

    return {"success": True, "message": "Invitation accepted."}


@router.post("/{trip_id}/share/decline")
@limiter.limit(RateLimits.TRIP_UPDATE)
async def decline_trip_invitation(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Decline an invitation to a trip.

    Changes invitation status from pending to declined.
    """
    # Find participant record for current user
    result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip_id,
            Participant.user_id == current_user.id
        )
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=404,
            detail="No invitation found for this trip."
        )

    if participant.invitation_status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Invitation is not pending."
        )

    # Decline invitation
    participant.invitation_status = InvitationStatus.DECLINED.value

    await db.commit()

    logger.info(
        "trip_invitation_declined",
        trip_id=trip_id,
        user_id=current_user.id
    )

    return {"success": True, "message": "Invitation declined."}


@router.delete("/{trip_id}/participants/{participant_id}", status_code=204)
@limiter.limit(RateLimits.TRIP_DELETE)
async def remove_participant(
    request: Request,
    trip_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove a participant from a trip.

    Owner can remove any participant.
    Participants can remove themselves (leave trip).
    """
    # Get trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Get participant
    result = await db.execute(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.trip_id == trip_id
        )
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Check permission: Owner can remove anyone, users can remove themselves
    is_owner = trip.owner_id == current_user.id or current_user.is_superuser
    is_self = participant.user_id == current_user.id

    if not is_owner and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove yourself or participants if you're the owner."
        )

    await db.delete(participant)
    await db.commit()

    logger.info(
        "participant_removed",
        trip_id=trip_id,
        participant_id=participant_id,
        removed_by=current_user.id
    )

    return None


