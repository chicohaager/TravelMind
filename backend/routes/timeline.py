"""
Timeline/Tagesplaner Router
Day-by-day schedule management for trips
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date, time
import math

router = APIRouter()

# In-Memory Storage
timeline_entries_db = {}
timeline_id_counter = 1


class TimelineEntryCreate(BaseModel):
    place_id: int = Field(..., description="ID of the place")
    day_date: date = Field(..., description="Date for this entry")
    start_time: Optional[time] = Field(None, description="Start time (optional)")
    end_time: Optional[time] = Field(None, description="End time (optional)")
    duration_minutes: Optional[int] = Field(None, description="Estimated duration in minutes")
    notes: Optional[str] = Field(None, description="Notes for this timeline entry")
    order: int = Field(default=0, description="Order within the day")


class TimelineEntryUpdate(BaseModel):
    day_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    order: Optional[int] = None


class TimelineEntryResponse(BaseModel):
    id: int
    trip_id: int
    place_id: int
    place_name: str
    place_category: Optional[str]
    place_latitude: float
    place_longitude: float
    day_date: date
    start_time: Optional[time]
    end_time: Optional[time]
    duration_minutes: Optional[int]
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
async def get_timeline(trip_id: int):
    """Get timeline for a trip, grouped by day"""
    from routes.places import places_db

    # Get all timeline entries for this trip
    entries = [e for e in timeline_entries_db.values() if e.get("trip_id") == trip_id]

    # Enrich with place data
    enriched_entries = []
    for entry in entries:
        place_id = entry.get("place_id")
        place = places_db.get(place_id)

        if place:
            enriched_entries.append({
                "id": entry["id"],
                "trip_id": entry["trip_id"],
                "place_id": place_id,
                "place_name": place.get("name", "Unbekannter Ort"),
                "place_category": place.get("category"),
                "place_latitude": place.get("latitude", 0),
                "place_longitude": place.get("longitude", 0),
                "day_date": entry["day_date"],
                "start_time": entry.get("start_time"),
                "end_time": entry.get("end_time"),
                "duration_minutes": entry.get("duration_minutes"),
                "notes": entry.get("notes"),
                "order": entry.get("order", 0),
                "created_at": entry["created_at"]
            })

    # Group by day
    days = {}
    for entry in enriched_entries:
        day_str = entry["day_date"]
        if day_str not in days:
            days[day_str] = []
        days[day_str].append(entry)

    # Sort entries within each day by order
    for day in days.values():
        day.sort(key=lambda x: x["order"])

    # Build response
    result = []
    for day_date, entries in sorted(days.items()):
        total_duration = sum(e.get("duration_minutes", 0) for e in entries)
        result.append({
            "day_date": day_date,
            "entries": entries,
            "total_duration_minutes": total_duration
        })

    return result


@router.post("/{trip_id}/timeline", response_model=TimelineEntryResponse, status_code=201)
async def create_timeline_entry(trip_id: int, entry: TimelineEntryCreate):
    """Add a place to the timeline"""
    from routes.places import places_db

    global timeline_id_counter

    # Validate place exists
    if entry.place_id not in places_db:
        raise HTTPException(status_code=404, detail="Place not found")

    place = places_db[entry.place_id]

    # Validate place belongs to trip
    if place.get("trip_id") != trip_id:
        raise HTTPException(status_code=400, detail="Place does not belong to this trip")

    # Get max order for this day
    day_entries = [
        e for e in timeline_entries_db.values()
        if e.get("trip_id") == trip_id and e.get("day_date") == entry.day_date
    ]
    max_order = max([e.get("order", 0) for e in day_entries], default=-1)

    new_entry = {
        "id": timeline_id_counter,
        "trip_id": trip_id,
        "place_id": entry.place_id,
        "day_date": entry.day_date.isoformat(),
        "start_time": entry.start_time.isoformat() if entry.start_time else None,
        "end_time": entry.end_time.isoformat() if entry.end_time else None,
        "duration_minutes": entry.duration_minutes,
        "notes": entry.notes,
        "order": max_order + 1,
        "created_at": datetime.now().isoformat()
    }

    timeline_entries_db[timeline_id_counter] = new_entry
    timeline_id_counter += 1

    # Build response with place data
    return {
        "id": new_entry["id"],
        "trip_id": trip_id,
        "place_id": entry.place_id,
        "place_name": place.get("name"),
        "place_category": place.get("category"),
        "place_latitude": place.get("latitude", 0),
        "place_longitude": place.get("longitude", 0),
        "day_date": entry.day_date,
        "start_time": entry.start_time,
        "end_time": entry.end_time,
        "duration_minutes": entry.duration_minutes,
        "notes": entry.notes,
        "order": new_entry["order"],
        "created_at": new_entry["created_at"]
    }


@router.put("/timeline/{entry_id}", response_model=TimelineEntryResponse)
async def update_timeline_entry(entry_id: int, entry: TimelineEntryUpdate):
    """Update a timeline entry"""
    from routes.places import places_db

    if entry_id not in timeline_entries_db:
        raise HTTPException(status_code=404, detail="Timeline entry not found")

    existing = timeline_entries_db[entry_id]

    # Update fields
    if entry.day_date is not None:
        existing["day_date"] = entry.day_date.isoformat()
    if entry.start_time is not None:
        existing["start_time"] = entry.start_time.isoformat()
    if entry.end_time is not None:
        existing["end_time"] = entry.end_time.isoformat()
    if entry.duration_minutes is not None:
        existing["duration_minutes"] = entry.duration_minutes
    if entry.notes is not None:
        existing["notes"] = entry.notes
    if entry.order is not None:
        existing["order"] = entry.order

    # Get place data for response
    place = places_db.get(existing["place_id"], {})

    return {
        "id": existing["id"],
        "trip_id": existing["trip_id"],
        "place_id": existing["place_id"],
        "place_name": place.get("name", "Unbekannter Ort"),
        "place_category": place.get("category"),
        "place_latitude": place.get("latitude", 0),
        "place_longitude": place.get("longitude", 0),
        "day_date": existing["day_date"],
        "start_time": existing.get("start_time"),
        "end_time": existing.get("end_time"),
        "duration_minutes": existing.get("duration_minutes"),
        "notes": existing.get("notes"),
        "order": existing.get("order", 0),
        "created_at": existing["created_at"]
    }


@router.delete("/timeline/{entry_id}", status_code=204)
async def delete_timeline_entry(entry_id: int):
    """Remove a place from the timeline"""
    if entry_id not in timeline_entries_db:
        raise HTTPException(status_code=404, detail="Timeline entry not found")

    del timeline_entries_db[entry_id]
    return None


@router.post("/{trip_id}/timeline/reorder")
async def reorder_timeline(trip_id: int, entry_ids: List[int]):
    """Reorder timeline entries (e.g., after drag & drop)"""
    for index, entry_id in enumerate(entry_ids):
        if entry_id in timeline_entries_db and timeline_entries_db[entry_id].get("trip_id") == trip_id:
            timeline_entries_db[entry_id]["order"] = index

    return {"success": True}


@router.post("/{trip_id}/timeline/optimize")
async def optimize_timeline(trip_id: int, day_date: date):
    """
    Optimize timeline order for a specific day based on geographic distance.
    Uses nearest-neighbor algorithm to minimize travel distance.
    """
    from routes.places import places_db

    # Get all entries for this day
    day_entries = [
        e for e in timeline_entries_db.values()
        if e.get("trip_id") == trip_id and e.get("day_date") == day_date.isoformat()
    ]

    if len(day_entries) <= 1:
        return {"success": True, "message": "Nicht genug Einträge zum Optimieren"}

    # Get place coordinates
    places_with_coords = []
    for entry in day_entries:
        place = places_db.get(entry["place_id"])
        if place:
            places_with_coords.append({
                "entry_id": entry["id"],
                "lat": place.get("latitude", 0),
                "lon": place.get("longitude", 0),
                "visited": place.get("visited", False)
            })

    if len(places_with_coords) <= 1:
        return {"success": True, "message": "Keine Koordinaten verfügbar"}

    # Nearest neighbor optimization
    # Start with first unvisited place, or first place if all unvisited
    unvisited_places = [p for p in places_with_coords if not p["visited"]]
    start_places = unvisited_places if unvisited_places else places_with_coords

    ordered = [start_places[0]]
    remaining = [p for p in places_with_coords if p["entry_id"] != ordered[0]["entry_id"]]

    while remaining:
        current = ordered[-1]
        # Find nearest remaining place
        nearest = min(
            remaining,
            key=lambda p: calculate_distance(current["lat"], current["lon"], p["lat"], p["lon"])
        )
        ordered.append(nearest)
        remaining = [p for p in remaining if p["entry_id"] != nearest["entry_id"]]

    # Update order
    for index, place_data in enumerate(ordered):
        timeline_entries_db[place_data["entry_id"]]["order"] = index

    return {
        "success": True,
        "message": f"{len(ordered)} Einträge optimiert",
        "reordered_count": len(ordered)
    }
