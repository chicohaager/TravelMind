"""
Admin Router
Admin-only endpoints for user and system management
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from models.audit_log import AuditLog
from models.database import get_db
from models.diary import DiaryEntry
from models.trip import Trip
from models.user import User
from pydantic import BaseModel, EmailStr
from routes.auth import UserRegister, get_current_active_user
from services.audit_service import audit_service
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.geocoding import geocode_if_missing
from utils.rate_limits import RateLimits, get_rate_limit_status, limiter

router = APIRouter()


# Admin Middleware
async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Require admin/superuser privileges

    Raises 403 Forbidden if user is not an admin.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


# Response Models
class UserListItem(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime

    # Statistics
    trip_count: Optional[int] = 0
    diary_count: Optional[int] = 0

    class Config:
        from_attributes = True


class UserAdminUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_trips: int
    total_diary_entries: int
    total_places: int


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    event_category: str
    user_id: Optional[int]
    username: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[int]
    ip_address: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    description: Optional[str]
    details: Optional[dict]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Endpoints
@router.get("/users", response_model=List[UserListItem])
@limiter.limit(RateLimits.ADMIN_READ)
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users (Admin only)

    Returns a paginated list of all users with basic statistics.
    Supports searching by username, email, or full name.
    """
    # Build optimized query with subqueries for counts (avoiding N+1 problem)
    # Subquery for trip count per user
    trip_count_subq = select(func.count(Trip.id)).where(Trip.owner_id == User.id).correlate(User).scalar_subquery()

    # Subquery for diary count per user
    diary_count_subq = (
        select(func.count(DiaryEntry.id)).where(DiaryEntry.author_id == User.id).correlate(User).scalar_subquery()
    )

    # Main query with counts
    query = select(User, trip_count_subq.label("trip_count"), diary_count_subq.label("diary_count"))

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_pattern))
            | (User.email.ilike(search_pattern))
            | (User.full_name.ilike(search_pattern))
        )

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    # Execute query - single query with all counts
    result = await db.execute(query)
    rows = result.all()

    # Build response list
    user_list = []
    for row in rows:
        user = row[0]  # User object
        trip_count = row[1] or 0  # trip_count
        diary_count = row[2] or 0  # diary_count

        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "trip_count": trip_count,
            "diary_count": diary_count,
        }
        user_list.append(UserListItem(**user_dict))

    return user_list


@router.get("/users/{user_id}")
@limiter.limit(RateLimits.ADMIN_READ)
async def get_user_admin(
    request: Request, user_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """
    Get detailed user information (Admin only)

    Returns full user details including sensitive information.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Import models for counting
    from models.diary import DiaryEntry
    from models.trip import Trip

    # Count trips for this user
    trip_count_result = await db.execute(select(func.count(Trip.id)).where(Trip.owner_id == user.id))
    trip_count = trip_count_result.scalar()

    # Count diary entries for this user
    diary_count_result = await db.execute(select(func.count(DiaryEntry.id)).where(DiaryEntry.author_id == user.id))
    diary_count = diary_count_result.scalar()

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "trip_count": trip_count,
        "diary_count": diary_count,
    }


@router.put("/users/{user_id}")
@limiter.limit(RateLimits.ADMIN_WRITE)
async def update_user_admin(
    user_id: int,
    user_update: UserAdminUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user (Admin only)

    Allows admins to modify user accounts including status and privileges.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from removing their own admin status
    if user.id == admin.id and user_update.is_superuser is False:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin privileges")

    # Check if email is being changed and already exists
    if user_update.email and user_update.email != user.email:
        email_check = await db.execute(select(User).where(User.email == user_update.email))
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.now()

    await db.commit()
    await db.refresh(user)

    # Audit log: admin user update
    await audit_service.log_admin_event(
        db=db,
        action="user_update",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_user_id=user.id,
        request=request,
        details={"updated_fields": list(update_data.keys()), "target_username": user.username},
    )

    return user


@router.delete("/users/{user_id}", status_code=204)
@limiter.limit(RateLimits.ADMIN_DELETE)
async def delete_user_admin(
    user_id: int, request: Request, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """
    Delete user (Admin only)

    Permanently deletes a user account and all associated data.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from deleting themselves
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account via admin panel")

    # Store user info for audit before deletion
    deleted_username = user.username
    deleted_email = user.email

    await db.delete(user)
    await db.commit()

    # Audit log: admin user deletion
    await audit_service.log_admin_event(
        db=db,
        action="user_delete",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_user_id=user_id,
        request=request,
        details={"deleted_username": deleted_username, "deleted_email": deleted_email},
    )

    return None


@router.get("/stats", response_model=SystemStats)
@limiter.limit(RateLimits.ADMIN_READ)
async def get_system_stats(request: Request, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """
    Get system statistics (Admin only)

    Returns overview statistics about the application.
    """
    # Import models for counting
    from models.diary import DiaryEntry
    from models.place import Place
    from models.trip import Trip

    # Count users
    total_users = await db.execute(select(func.count(User.id)))
    total_users = total_users.scalar()

    active_users = await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
    active_users = active_users.scalar()

    # Count trips
    total_trips = await db.execute(select(func.count(Trip.id)))
    total_trips = total_trips.scalar()

    # Count diary entries
    total_diary_entries = await db.execute(select(func.count(DiaryEntry.id)))
    total_diary_entries = total_diary_entries.scalar()

    # Count places
    total_places = await db.execute(select(func.count(Place.id)))
    total_places = total_places.scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_trips": total_trips,
        "total_diary_entries": total_diary_entries,
        "total_places": total_places,
    }


# ==================== SETTINGS MANAGEMENT ====================


class SettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str]
    value_type: str
    description: Optional[str]

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str
    value_type: Optional[str] = None
    description: Optional[str] = None


@router.get("/settings", response_model=List[SettingResponse])
@limiter.limit(RateLimits.ADMIN_READ)
async def get_all_settings(request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """
    Get all application settings
    Admin only
    """
    from models.settings import Settings

    result = await db.execute(select(Settings))
    settings = result.scalars().all()

    return settings


@router.get("/settings/{key}")
@limiter.limit(RateLimits.ADMIN_READ)
async def get_setting_by_key(
    request: Request, key: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Get a specific setting by key
    Admin only
    """
    from models.settings import Settings

    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    return {
        "key": setting.key,
        "value": setting.value,
        "typed_value": setting.get_typed_value(),
        "value_type": setting.value_type,
        "description": setting.description,
    }


@router.put("/settings/{key}")
@limiter.limit(RateLimits.ADMIN_WRITE)
async def update_setting(
    key: str,
    update: SettingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Update a setting value
    Admin only
    """
    from utils.settings_manager import set_setting

    setting = await set_setting(db, key, update.value, value_type=update.value_type, description=update.description)

    # Audit log: settings change
    await audit_service.log_admin_event(
        db=db,
        action="settings_change",
        admin_user_id=admin.id,
        admin_username=admin.username,
        request=request,
        details={"key": key, "new_value": update.value},
    )

    return {
        "message": f"Setting '{key}' updated successfully",
        "key": setting.key,
        "value": setting.value,
        "typed_value": setting.get_typed_value(),
    }


@router.post("/settings/registration/toggle")
@limiter.limit(RateLimits.ADMIN_WRITE)
async def toggle_registration(
    request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Toggle registration open/closed
    Admin only
    """
    from utils.settings_manager import get_setting, set_setting

    current_value = await get_setting(db, "registration_open", default=True)
    new_value = not current_value

    await set_setting(db, "registration_open", str(new_value).lower(), "boolean")

    # Audit log: registration toggle
    await audit_service.log_admin_event(
        db=db,
        action="settings_change",
        admin_user_id=admin.id,
        admin_username=admin.username,
        request=request,
        details={"key": "registration_open", "new_value": new_value},
    )

    return {"message": f"Registrierung {'geöffnet' if new_value else 'geschlossen'}", "registration_open": new_value}


@router.post("/users/create")
@limiter.limit(RateLimits.ADMIN_WRITE)
async def admin_create_user(
    user_data: UserRegister, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Admin can create users even when registration is closed
    Admin only
    """
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=User.hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Audit log: admin user creation
    await audit_service.log_admin_event(
        db=db,
        action="user_create",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_user_id=new_user.id,
        request=request,
        details={"created_username": new_user.username, "created_email": new_user.email},
    )

    return {
        "message": "User created successfully by admin",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
        },
    }


# ==================== GEOCODING UTILITIES ====================


@router.post("/geocode/fix-places")
@limiter.limit(RateLimits.ADMIN_WRITE)
async def batch_geocode_places(
    request: Request, force_all: bool = False, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Batch geocode places with missing or potentially incorrect coordinates
    Admin only - fixes data quality issues

    By default, only fixes places with coordinates near 0,0 or obviously wrong
    (outside the expected region for the trip). Set force_all=True to geocode all places.
    """
    from models.place import Place
    from models.trip import Trip

    if force_all:
        # Geocode ALL places
        result = await db.execute(select(Place))
        places_to_fix = result.scalars().all()
    else:
        # Find places with missing or suspicious coordinates
        # This includes: 0,0 coordinates OR coordinates that seem wrong
        result = await db.execute(select(Place))
        all_places = result.scalars().all()

        places_to_fix = []
        for place in all_places:
            # Check if coordinates are 0,0 or None
            if abs(place.latitude) < 0.001 and abs(place.longitude) < 0.001:
                places_to_fix.append(place)
                continue

            # Get trip for this place to check if coordinates are in reasonable region
            trip_result = await db.execute(select(Trip).where(Trip.id == place.trip_id))
            trip = trip_result.scalar_one_or_none()

            if trip and hasattr(trip, "latitude") and hasattr(trip, "longitude"):
                # Check if place is very far from trip location (>500km = ~5 degrees)
                if trip.latitude and trip.longitude:
                    lat_diff = abs(place.latitude - trip.latitude)
                    lon_diff = abs(place.longitude - trip.longitude)
                    if lat_diff > 5 or lon_diff > 5:
                        places_to_fix.append(place)
                        continue

    if not places_to_fix:
        return {"message": "No places found with missing coordinates", "fixed_count": 0}

    fixed_count = 0
    failed_places = []

    for place in places_to_fix:
        # Get trip for destination context
        trip_result = await db.execute(select(Trip).where(Trip.id == place.trip_id))
        trip = trip_result.scalar_one_or_none()

        destination = trip.destination if trip and hasattr(trip, "destination") else None

        # Geocode the place
        try:
            position = await geocode_if_missing(
                name=place.name,
                latitude=place.latitude,
                longitude=place.longitude,
                address=place.address,
                destination=destination,
            )

            # `abs(new_lat)` stand hier bis zum 2026-08-26 — und stuerzt ab,
            # seit die Suche bei Misserfolg (None, None) zurueckgibt statt
            # 0.0/0.0: `abs(None)` wirft TypeError. Der Fehler landete im
            # `except` darunter und erschien dem Verwalter als Grund
            # "unsupported operand", also als Eigenschaft des ORTES statt als
            # Fehlschlag der Suche.
            if position.lat is None or position.lon is None:
                failed_places.append({"id": place.id, "name": place.name, "reason": "Keine Position gefunden"})
            else:
                place.latitude = position.lat
                place.longitude = position.lon
                place.position_nur_ort = position.nur_ort
                place.updated_at = datetime.now()
                fixed_count += 1

        except Exception as e:
            failed_places.append({"id": place.id, "name": place.name, "reason": str(e)})

    await db.commit()

    return {
        "message": f"Successfully geocoded {fixed_count} places",
        "fixed_count": fixed_count,
        "total_found": len(places_to_fix),
        "failed_count": len(failed_places),
        "failed_places": failed_places[:10],  # Only show first 10 failures
    }


# ==================== AUDIT LOG ENDPOINTS ====================


@router.get("/audit-logs", response_model=List[AuditLogResponse])
@limiter.limit(RateLimits.ADMIN_READ)
async def get_audit_logs(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    event_category: Optional[str] = None,
    user_id: Optional[int] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit logs (Admin only)

    Returns paginated audit logs with optional filtering.

    Filters:
    - **event_category**: Filter by category (auth, data, admin, security)
    - **user_id**: Filter by user ID
    - **event_type**: Filter by event type (e.g., auth.login, trip.create)
    - **status**: Filter by status (success, failure, warning)
    """
    limit = min(limit, 500)

    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if event_category:
        query = query.where(AuditLog.event_category == event_category)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if status:
        query = query.where(AuditLog.status == status)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


@router.get("/audit-logs/stats")
@limiter.limit(RateLimits.ADMIN_READ)
async def get_audit_stats(request: Request, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """
    Get audit log statistics (Admin only)

    Returns counts and summaries of audit events.
    """
    from sqlalchemy import func

    # Total counts by category
    category_result = await db.execute(
        select(AuditLog.event_category, func.count(AuditLog.id)).group_by(AuditLog.event_category)
    )
    category_counts = dict(category_result.all())

    # Failed events in last 24 hours
    from datetime import timedelta, timezone

    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.status == "failure").where(AuditLog.created_at > yesterday)
    )
    failed_24h = failed_result.scalar() or 0

    # Recent security events
    security_result = await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.event_category == "security")
        .where(AuditLog.created_at > yesterday)
    )
    security_24h = security_result.scalar() or 0

    # Total events
    total_result = await db.execute(select(func.count(AuditLog.id)))
    total_events = total_result.scalar() or 0

    return {
        "total_events": total_events,
        "by_category": category_counts,
        "failed_last_24h": failed_24h,
        "security_events_24h": security_24h,
    }


# ==================== RATE LIMITING CONFIG ====================


@router.get("/rate-limits")
@limiter.limit(RateLimits.ADMIN_READ)
async def get_rate_limits(request: Request, admin: User = Depends(require_admin)):
    """
    Get current rate limit configuration (Admin only)

    Returns all configured rate limits for API endpoints.
    Limits can be customized via environment variables.
    """
    return {
        "message": "Current rate limit configuration",
        "limits": get_rate_limit_status(),
        "note": "Limits can be customized via RATE_LIMIT_* environment variables",
    }
