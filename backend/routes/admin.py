"""
Admin Router
Admin-only endpoints for user and system management
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

from models.database import get_db
from models.user import User
from routes.auth import get_current_active_user, UserRegister
from utils.geocoding import geocode_if_missing

router = APIRouter()


# Admin Middleware
async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Require admin/superuser privileges

    Raises 403 Forbidden if user is not an admin.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
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


# Endpoints
@router.get("/users", response_model=List[UserListItem])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (Admin only)

    Returns a paginated list of all users with basic statistics.
    Supports searching by username, email, or full name.
    """
    # Build query
    query = select(User)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern)) |
            (User.full_name.ilike(search_pattern))
        )

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Import models for counting
    from models.trip import Trip
    from models.diary import DiaryEntry

    # For each user, get trip and diary counts
    user_list = []
    for user in users:
        # Count trips for this user
        trip_count_result = await db.execute(
            select(func.count(Trip.id)).where(Trip.owner_id == user.id)
        )
        trip_count = trip_count_result.scalar()

        # Count diary entries for this user
        diary_count_result = await db.execute(
            select(func.count(DiaryEntry.id)).where(DiaryEntry.author_id == user.id)
        )
        diary_count = diary_count_result.scalar()

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
            "diary_count": diary_count
        }
        user_list.append(UserListItem(**user_dict))

    return user_list


@router.get("/users/{user_id}")
async def get_user_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
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
    from models.trip import Trip
    from models.diary import DiaryEntry

    # Count trips for this user
    trip_count_result = await db.execute(
        select(func.count(Trip.id)).where(Trip.owner_id == user.id)
    )
    trip_count = trip_count_result.scalar()

    # Count diary entries for this user
    diary_count_result = await db.execute(
        select(func.count(DiaryEntry.id)).where(DiaryEntry.author_id == user.id)
    )
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
        "diary_count": diary_count
    }


@router.put("/users/{user_id}")
async def update_user_admin(
    user_id: int,
    user_update: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
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
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own admin privileges"
        )

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

    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
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
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account via admin panel"
        )

    await db.delete(user)
    await db.commit()

    return None


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system statistics (Admin only)

    Returns overview statistics about the application.
    """
    # Import models for counting
    from models.trip import Trip
    from models.diary import DiaryEntry
    from models.place import Place

    # Count users
    total_users = await db.execute(select(func.count(User.id)))
    total_users = total_users.scalar()

    active_users = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
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
        "total_places": total_places
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
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get all application settings
    Admin only
    """
    from models.settings import Settings

    result = await db.execute(select(Settings))
    settings = result.scalars().all()

    return settings


@router.get("/settings/{key}")
async def get_setting_by_key(
    key: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get a specific setting by key
    Admin only
    """
    from utils.settings_manager import get_setting
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
        "description": setting.description
    }


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Update a setting value
    Admin only
    """
    from utils.settings_manager import set_setting

    setting = await set_setting(
        db,
        key,
        update.value,
        value_type=update.value_type,
        description=update.description
    )

    return {
        "message": f"Setting '{key}' updated successfully",
        "key": setting.key,
        "value": setting.value,
        "typed_value": setting.get_typed_value()
    }


@router.post("/settings/registration/toggle")
async def toggle_registration(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Toggle registration open/closed
    Admin only
    """
    from utils.settings_manager import get_setting, set_setting

    current_value = await get_setting(db, "registration_open", default=True)
    new_value = not current_value

    await set_setting(db, "registration_open", str(new_value).lower(), "boolean")

    return {
        "message": f"Registrierung {'geöffnet' if new_value else 'geschlossen'}",
        "registration_open": new_value
    }


@router.post("/users/create")
async def admin_create_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Admin can create users even when registration is closed
    Admin only
    """
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=User.hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "User created successfully by admin",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name
        }
    }


# ==================== GEOCODING UTILITIES ====================

@router.post("/geocode/fix-places")
async def batch_geocode_places(
    force_all: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
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
            if (abs(place.latitude) < 0.001 and abs(place.longitude) < 0.001):
                places_to_fix.append(place)
                continue

            # Get trip for this place to check if coordinates are in reasonable region
            trip_result = await db.execute(
                select(Trip).where(Trip.id == place.trip_id)
            )
            trip = trip_result.scalar_one_or_none()

            if trip and hasattr(trip, 'latitude') and hasattr(trip, 'longitude'):
                # Check if place is very far from trip location (>500km = ~5 degrees)
                if trip.latitude and trip.longitude:
                    lat_diff = abs(place.latitude - trip.latitude)
                    lon_diff = abs(place.longitude - trip.longitude)
                    if lat_diff > 5 or lon_diff > 5:
                        places_to_fix.append(place)
                        continue

    if not places_to_fix:
        return {
            "message": "No places found with missing coordinates",
            "fixed_count": 0
        }

    fixed_count = 0
    failed_places = []

    for place in places_to_fix:
        # Get trip for destination context
        trip_result = await db.execute(
            select(Trip).where(Trip.id == place.trip_id)
        )
        trip = trip_result.scalar_one_or_none()

        destination = trip.destination if trip and hasattr(trip, 'destination') else None

        # Geocode the place
        try:
            new_lat, new_lon = await geocode_if_missing(
                name=place.name,
                latitude=place.latitude,
                longitude=place.longitude,
                address=place.address,
                destination=destination
            )

            # Check if coordinates actually changed
            if abs(new_lat) > 0.001 or abs(new_lon) > 0.001:
                place.latitude = new_lat
                place.longitude = new_lon
                place.updated_at = datetime.now()
                fixed_count += 1
            else:
                failed_places.append({
                    "id": place.id,
                    "name": place.name,
                    "reason": "Geocoding returned 0,0"
                })

        except Exception as e:
            failed_places.append({
                "id": place.id,
                "name": place.name,
                "reason": str(e)
            })

    await db.commit()

    return {
        "message": f"Successfully geocoded {fixed_count} places",
        "fixed_count": fixed_count,
        "total_found": len(places_to_fix),
        "failed_count": len(failed_places),
        "failed_places": failed_places[:10]  # Only show first 10 failures
    }
