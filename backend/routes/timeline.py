"""
Timeline/Tagesplaner Router
Day-by-day schedule management for trips using Place visit_date
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import math

from models.database import get_db
from models.place import Place
from models.trip import Trip
from models.user import User
from routes.auth import get_current_active_user

router = APIRouter()


class TimelineEntryResponse(BaseModel):
    id: int
    trip_id: int
    place_id: int
    place_name: str
    place_category: Optional[str]
    place_latitude: float
    place_longitude: float
    day_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str]
    order: int
    created_at: datetime

    class Config:
        from_attributes = True


class DaySchedule(BaseModel):
    """Grouped schedule for one day"""
    day_date: date
    entries: List[TimelineEntryResponse]
    total_duration_minutes: int


class TimelineEntryUpdate(BaseModel):
    visit_date: Optional[date] = None
    order: Optional[int] = None
    notes: Optional[str] = None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers (Haversine formula)"""
    R = 6371  # Earth radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


@router.get("/{trip_id}/timeline", response_model=List[DaySchedule])
async def get_timeline(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get timeline for a trip, grouped by day. Requires authentication and trip ownership."""
    # Verify trip exists and user has access
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify trip ownership
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all places with visit_date set
    result = await db.execute(
        select(Place)
        .where(and_(Place.trip_id == trip_id, Place.visit_date.isnot(None)))
        .order_by(Place.visit_date, Place.order)
    )
    places = result.scalars().all()

    # Group by day
    days = {}
    for place in places:
        day_date = place.visit_date.date() if isinstance(place.visit_date, datetime) else place.visit_date
        day_str = day_date.isoformat()

        if day_str not in days:
            days[day_str] = []

        entry = TimelineEntryResponse(
            id=place.id,
            trip_id=trip_id,
            place_id=place.id,
            place_name=place.name,
            place_category=place.category,
            place_latitude=place.latitude,
            place_longitude=place.longitude,
            day_date=day_date,
            start_time=None,
            end_time=None,
            duration_minutes=None,
            notes=place.notes,
            order=place.order or 0,
            created_at=place.created_at or datetime.now()
        )
        days[day_str].append(entry)

    # Sort entries within each day by order
    for day in days.values():
        day.sort(key=lambda x: x.order)

    # Build response
    result = []
    for day_date_str, entries in sorted(days.items()):
        total_duration = sum(e.duration_minutes or 0 for e in entries)
        result.append(DaySchedule(
            day_date=date.fromisoformat(day_date_str),
            entries=entries,
            total_duration_minutes=total_duration
        ))

    return result


@router.put("/{trip_id}/timeline/{place_id}")
async def update_timeline_entry(
    trip_id: int,
    place_id: int,
    update_data: TimelineEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a place's timeline data (visit_date, order, notes). Requires authentication."""
    # Verify trip ownership first
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Place).where(and_(Place.id == place_id, Place.trip_id == trip_id))
    )
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    if update_data.visit_date is not None:
        place.visit_date = datetime.combine(update_data.visit_date, datetime.min.time())
    if update_data.order is not None:
        place.order = update_data.order
    if update_data.notes is not None:
        place.notes = update_data.notes

    await db.commit()
    await db.refresh(place)

    return {"success": True, "place_id": place.id}


class TimelineEntryCreate(BaseModel):
    """Request body for creating a timeline entry"""
    place_id: int
    day_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    order: Optional[int] = 0


@router.post("/{trip_id}/timeline", response_model=TimelineEntryResponse, status_code=201)
async def create_timeline_entry(
    trip_id: int,
    entry: TimelineEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a place to the timeline by setting its visit_date. Requires authentication."""
    # Verify trip ownership first
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get the place
    result = await db.execute(
        select(Place).where(and_(Place.id == entry.place_id, Place.trip_id == trip_id))
    )
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Get max order for this day
    result = await db.execute(
        select(Place)
        .where(and_(
            Place.trip_id == trip_id,
            Place.visit_date.isnot(None)
        ))
    )
    all_places = result.scalars().all()

    day_places = [p for p in all_places if p.visit_date and p.visit_date.date() == entry.day_date]
    max_order = max([p.order or 0 for p in day_places], default=-1)

    # Update place with timeline data
    place.visit_date = datetime.combine(entry.day_date, datetime.min.time())
    place.order = entry.order if entry.order else max_order + 1
    if entry.notes:
        place.notes = entry.notes

    await db.commit()
    await db.refresh(place)

    # Return TimelineEntryResponse
    return TimelineEntryResponse(
        id=place.id,
        trip_id=trip_id,
        place_id=place.id,
        place_name=place.name,
        place_category=place.category,
        place_latitude=place.latitude,
        place_longitude=place.longitude,
        day_date=entry.day_date,
        start_time=entry.start_time,
        end_time=entry.end_time,
        duration_minutes=entry.duration_minutes,
        notes=place.notes,
        order=place.order or 0,
        created_at=place.created_at or datetime.now()
    )


@router.delete("/{trip_id}/timeline/{place_id}")
async def remove_from_timeline(
    trip_id: int,
    place_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a place from the timeline by clearing its visit_date. Requires authentication."""
    # Verify trip ownership first
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Place).where(and_(Place.id == place_id, Place.trip_id == trip_id))
    )
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    place.visit_date = None
    place.order = 0

    await db.commit()

    return {"success": True}


@router.post("/{trip_id}/timeline/reorder")
async def reorder_timeline(
    trip_id: int,
    place_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reorder timeline entries (e.g., after drag & drop). Requires authentication."""
    # Verify trip ownership first
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    for index, place_id in enumerate(place_ids):
        result = await db.execute(
            select(Place).where(and_(Place.id == place_id, Place.trip_id == trip_id))
        )
        place = result.scalar_one_or_none()
        if place:
            place.order = index

    await db.commit()
    return {"success": True}


@router.post("/{trip_id}/timeline/optimize")
async def optimize_timeline(
    trip_id: int,
    day_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Optimize timeline order for a specific day based on geographic distance.
    Uses nearest-neighbor algorithm to minimize travel distance.
    Requires authentication.
    """
    # Verify trip ownership first
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all places for this day
    result = await db.execute(
        select(Place)
        .where(and_(Place.trip_id == trip_id, Place.visit_date.isnot(None)))
    )
    all_places = result.scalars().all()

    day_places = [p for p in all_places if p.visit_date and p.visit_date.date() == day_date]

    if len(day_places) <= 1:
        return {"success": True, "message": "Nicht genug Einträge zum Optimieren"}

    # Get place coordinates
    places_with_coords = []
    for place in day_places:
        places_with_coords.append({
            "place": place,
            "lat": place.latitude,
            "lon": place.longitude,
            "visited": place.visited
        })

    if len(places_with_coords) <= 1:
        return {"success": True, "message": "Keine Koordinaten verfügbar"}

    # Nearest neighbor optimization
    unvisited_places = [p for p in places_with_coords if not p["visited"]]
    start_places = unvisited_places if unvisited_places else places_with_coords

    ordered = [start_places[0]]
    remaining = [p for p in places_with_coords if p["place"].id != ordered[0]["place"].id]

    while remaining:
        current = ordered[-1]
        nearest = min(
            remaining,
            key=lambda p: calculate_distance(current["lat"], current["lon"], p["lat"], p["lon"])
        )
        ordered.append(nearest)
        remaining = [p for p in remaining if p["place"].id != nearest["place"].id]

    # Update order
    for index, place_data in enumerate(ordered):
        place_data["place"].order = index

    await db.commit()

    return {
        "success": True,
        "message": f"{len(ordered)} Einträge optimiert",
        "reordered_count": len(ordered)
    }
