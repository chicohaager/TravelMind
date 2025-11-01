"""
API routes for Route management (itineraries on maps)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from models.database import get_db
from models.route import Route
from models.trip import Trip
from routes.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/api/routes", tags=["routes"])


# Pydantic schemas
class RouteCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#6366F1"
    line_style: str = "solid"
    line_width: int = 3
    place_ids: List[int] = []
    total_distance: Optional[float] = None
    estimated_duration: Optional[int] = None
    transport_mode: str = "car"
    trip_id: int


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    line_style: Optional[str] = None
    line_width: Optional[int] = None
    place_ids: Optional[List[int]] = None
    total_distance: Optional[float] = None
    estimated_duration: Optional[int] = None
    transport_mode: Optional[str] = None
    order: Optional[int] = None


class RouteResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: str
    line_style: str
    line_width: int
    place_ids: List[int]
    total_distance: Optional[float]
    estimated_duration: Optional[int]
    transport_mode: str
    order: int
    trip_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Routes
@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    route_data: RouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new route for a trip
    """
    # Verify trip exists and belongs to user
    result = await db.execute(select(Trip).where(Trip.id == route_data.trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    if trip.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add routes to this trip"
        )

    # Create route
    route = Route(**route_data.model_dump())
    db.add(route)
    await db.commit()
    await db.refresh(route)

    return route


@router.get("/trip/{trip_id}", response_model=List[RouteResponse])
async def get_trip_routes(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all routes for a trip
    """
    # Verify trip exists and belongs to user
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    if trip.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view routes for this trip"
        )

    # Get routes
    result = await db.execute(
        select(Route)
        .where(Route.trip_id == trip_id)
        .order_by(Route.order, Route.created_at)
    )
    routes = result.scalars().all()

    return routes


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific route by ID
    """
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )

    # Verify user owns the trip
    result = await db.execute(select(Trip).where(Trip.id == route.trip_id))
    trip = result.scalar_one()

    if trip.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this route"
        )

    return route


@router.put("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int,
    route_data: RouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a route
    """
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )

    # Verify user owns the trip
    result = await db.execute(select(Trip).where(Trip.id == route.trip_id))
    trip = result.scalar_one()

    if trip.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this route"
        )

    # Update fields
    update_data = route_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(route, field, value)

    await db.commit()
    await db.refresh(route)

    return route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a route
    """
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )

    # Verify user owns the trip
    result = await db.execute(select(Trip).where(Trip.id == route.trip_id))
    trip = result.scalar_one()

    if trip.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this route"
        )

    await db.delete(route)
    await db.commit()

    return None
