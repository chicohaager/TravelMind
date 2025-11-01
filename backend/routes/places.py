"""
Places Router
CRUD operations for places/POIs in trips
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address
import structlog
import uuid
import magic
from pathlib import Path

from models.database import get_db
from models.place import Place
from models.place_list import PlaceList
from models.trip import Trip
from models.user import User
from routes.auth import get_optional_user, get_current_active_user
from services.guide_parser import guide_parser_service
from utils.geocoding import geocode_if_missing

logger = structlog.get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Upload configuration
UPLOAD_DIR = Path("./uploads/places")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_photo_type(contents: bytes, filename: str) -> bool:
    """
    Validate photo file type by checking actual content, not just extension.
    Uses python-magic to detect MIME type from file content.
    """
    extension = filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False

    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(contents)

    return mime_type in ALLOWED_MIME_TYPES


async def verify_trip_access(trip_id: int, user: User, db: AsyncSession) -> Trip:
    """
    Verify trip exists and user has access.
    Returns the trip if successful, raises HTTPException otherwise.
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.owner_id != user.id:
        logger.warning("unauthorized_trip_access", trip_id=trip_id, user_id=user.id, owner_id=trip.owner_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this trip"
        )

    return trip


class PlaceListCreate(BaseModel):
    title: str = Field(..., example="Restaurants", description="Title of the place list")
    icon: Optional[str] = Field("📍", example="🍽️", description="Emoji icon for the list")
    color: Optional[str] = Field("#6366F1", example="#F59E0B", description="Hex color code")
    is_collapsed: bool = Field(default=False)


class PlaceListResponse(BaseModel):
    id: int
    trip_id: int
    title: str
    icon: str
    color: str
    is_collapsed: bool
    place_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PlaceCreate(BaseModel):
    name: str = Field(..., example="Castelo de São Jorge")
    description: Optional[str] = Field(None, example="Historische Burg mit Aussicht")
    address: Optional[str] = None
    latitude: float = Field(..., example=38.7139, ge=-90, le=90)
    longitude: float = Field(..., example=-9.1334, ge=-180, le=180)
    category: Optional[str] = Field(None, example="sight")
    list_id: Optional[int] = Field(None, description="ID of the custom place list this belongs to")
    visit_date: Optional[datetime] = None
    visited: bool = Field(default=False)
    website: Optional[str] = None
    phone: Optional[str] = None
    cost: Optional[float] = None
    currency: str = Field(default="EUR")
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None
    photos: List[str] = Field(default=[])
    # External data from guide scraping
    external_rating: Optional[float] = Field(None, description="External rating from sources like TripAdvisor")
    review_count: Optional[int] = Field(None, description="Number of external reviews")
    opening_hours: Optional[str] = Field(None, description="Opening hours text")
    external_links: Optional[dict] = Field(None, description="Links to external services")


class PlaceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    address: Optional[str]
    latitude: float
    longitude: float
    category: Optional[str]
    list_id: Optional[int]
    visit_date: Optional[datetime]
    visited: bool
    website: Optional[str]
    phone: Optional[str]
    cost: Optional[float]
    currency: str
    rating: Optional[int]
    notes: Optional[str]
    photos: List[str]
    order: int
    created_at: datetime
    external_rating: Optional[float]
    review_count: Optional[int]
    opening_hours: Optional[str]
    external_links: Optional[dict]

    class Config:
        from_attributes = True


@router.get("/{trip_id}/places", response_model=List[PlaceResponse])
@limiter.limit("60/minute")
async def get_places(
    request: Request,
    trip_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all places for a trip with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 500)
    """
    # Enforce maximum limit
    limit = min(limit, 500)

    # Verify trip access
    await verify_trip_access(trip_id, current_user, db)

    # Get places with pagination
    result = await db.execute(
        select(Place)
        .where(Place.trip_id == trip_id)
        .order_by(Place.order)
        .offset(skip)
        .limit(limit)
    )
    places = result.scalars().all()

    logger.info("places_fetched", trip_id=trip_id, user_id=current_user.id, count=len(places))

    return places


@router.post("/{trip_id}/places", response_model=PlaceResponse, status_code=201)
@limiter.limit("30/minute")
async def create_place(
    request: Request,
    trip_id: int,
    place: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a new place to a trip. Requires authentication and trip ownership."""
    # Verify trip access
    trip = await verify_trip_access(trip_id, current_user, db)

    # Geocode if coordinates are missing
    latitude, longitude = await geocode_if_missing(
        name=place.name,
        latitude=place.latitude,
        longitude=place.longitude,
        address=place.address,
        destination=trip.destination if hasattr(trip, 'destination') else None
    )

    # Get max order for this trip
    result = await db.execute(
        select(func.max(Place.order))
        .where(Place.trip_id == trip_id)
    )
    max_order = result.scalar() or 0

    # Create new place
    new_place = Place(
        trip_id=trip_id,
        name=place.name,
        description=place.description,
        address=place.address,
        latitude=latitude,
        longitude=longitude,
        category=place.category,
        list_id=place.list_id,
        visit_date=place.visit_date,
        visited=place.visited,
        website=place.website,
        phone=place.phone,
        cost=place.cost,
        currency=place.currency,
        rating=place.rating,
        notes=place.notes,
        photos=place.photos,
        order=max_order + 1,
        external_rating=place.external_rating,
        review_count=place.review_count,
        opening_hours=place.opening_hours,
        external_links=place.external_links
    )

    db.add(new_place)
    await db.commit()
    await db.refresh(new_place)

    logger.info("place_created", place_id=new_place.id, trip_id=trip_id, user_id=current_user.id)

    return new_place


@router.put("/places/{place_id}", response_model=PlaceResponse)
@limiter.limit("30/minute")
async def update_place(
    request: Request,
    place_id: int,
    place: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a place. Requires authentication and trip ownership."""
    # Get existing place
    result = await db.execute(select(Place).where(Place.id == place_id))
    existing_place = result.scalar_one_or_none()

    if not existing_place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Verify ownership via trip
    await verify_trip_access(existing_place.trip_id, current_user, db)

    # Update fields
    existing_place.name = place.name
    existing_place.description = place.description
    existing_place.address = place.address
    existing_place.latitude = place.latitude
    existing_place.longitude = place.longitude
    existing_place.category = place.category
    existing_place.list_id = place.list_id
    existing_place.visit_date = place.visit_date
    existing_place.visited = place.visited
    existing_place.website = place.website
    existing_place.phone = place.phone
    existing_place.cost = place.cost
    existing_place.currency = place.currency
    existing_place.rating = place.rating
    existing_place.notes = place.notes
    existing_place.photos = place.photos
    existing_place.external_rating = place.external_rating
    existing_place.review_count = place.review_count
    existing_place.opening_hours = place.opening_hours
    existing_place.external_links = place.external_links
    existing_place.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(existing_place)

    logger.info("place_updated", place_id=place_id, trip_id=existing_place.trip_id, user_id=current_user.id)

    return existing_place


@router.delete("/places/{place_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_place(
    request: Request,
    place_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a place. Requires authentication and trip ownership."""
    # Get existing place
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Verify ownership via trip
    await verify_trip_access(place.trip_id, current_user, db)

    await db.delete(place)
    await db.commit()

    logger.info("place_deleted", place_id=place_id, trip_id=place.trip_id, user_id=current_user.id)

    return None


@router.put("/places/{place_id}/visited")
@limiter.limit("30/minute")
async def mark_as_visited(
    request: Request,
    place_id: int,
    visited: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a place as visited or not visited. Requires authentication and trip ownership."""
    # Get existing place
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Verify ownership via trip
    await verify_trip_access(place.trip_id, current_user, db)

    place.visited = visited
    place.updated_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info("place_visited_marked", place_id=place_id, visited=visited, user_id=current_user.id)

    return {"success": True, "visited": visited}


@router.post("/{trip_id}/places/reorder")
@limiter.limit("30/minute")
async def reorder_places(
    request: Request,
    trip_id: int,
    place_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reorder places for a trip. Requires authentication and trip ownership."""
    # Verify trip access
    await verify_trip_access(trip_id, current_user, db)

    # Update order for each place
    for index, place_id in enumerate(place_ids):
        result = await db.execute(
            select(Place)
            .where(Place.id == place_id)
            .where(Place.trip_id == trip_id)
        )
        place = result.scalar_one_or_none()
        if place:
            place.order = index
            place.updated_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info("places_reordered", trip_id=trip_id, count=len(place_ids), user_id=current_user.id)

    return {"success": True}


# ============ Custom Place Lists Endpoints ============

@router.get("/{trip_id}/lists", response_model=List[PlaceListResponse])
@limiter.limit("60/minute")
async def get_place_lists(
    request: Request,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all custom place lists for a trip. Requires authentication and trip ownership."""
    # Verify trip access
    await verify_trip_access(trip_id, current_user, db)

    # Get lists with place counts
    result = await db.execute(
        select(PlaceList)
        .where(PlaceList.trip_id == trip_id)
        .order_by(PlaceList.created_at)
    )
    lists = result.scalars().all()

    # Add place count for each list
    response_lists = []
    for lst in lists:
        result = await db.execute(
            select(func.count(Place.id))
            .where(Place.list_id == lst.id)
        )
        place_count = result.scalar() or 0

        response_lists.append(PlaceListResponse(
            id=lst.id,
            trip_id=lst.trip_id,
            title=lst.title,
            icon=lst.icon,
            color=lst.color,
            is_collapsed=lst.is_collapsed,
            place_count=place_count,
            created_at=lst.created_at
        ))

    logger.info("place_lists_fetched", trip_id=trip_id, count=len(response_lists), user_id=current_user.id)

    return response_lists


@router.post("/{trip_id}/lists", response_model=PlaceListResponse, status_code=201)
@limiter.limit("30/minute")
async def create_place_list(
    request: Request,
    trip_id: int,
    place_list: PlaceListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new custom place list. Requires authentication and trip ownership."""
    # Verify trip access
    await verify_trip_access(trip_id, current_user, db)

    # Create new list
    new_list = PlaceList(
        trip_id=trip_id,
        title=place_list.title,
        icon=place_list.icon or "📍",
        color=place_list.color or "#6366F1",
        is_collapsed=place_list.is_collapsed
    )

    db.add(new_list)
    await db.commit()
    await db.refresh(new_list)

    logger.info("place_list_created", list_id=new_list.id, trip_id=trip_id, user_id=current_user.id)

    return PlaceListResponse(
        id=new_list.id,
        trip_id=new_list.trip_id,
        title=new_list.title,
        icon=new_list.icon,
        color=new_list.color,
        is_collapsed=new_list.is_collapsed,
        place_count=0,
        created_at=new_list.created_at
    )


@router.put("/lists/{list_id}", response_model=PlaceListResponse)
@limiter.limit("30/minute")
async def update_place_list(
    request: Request,
    list_id: int,
    place_list: PlaceListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a custom place list. Requires authentication and trip ownership."""
    # Get existing list
    result = await db.execute(select(PlaceList).where(PlaceList.id == list_id))
    existing_list = result.scalar_one_or_none()

    if not existing_list:
        raise HTTPException(status_code=404, detail="Place list not found")

    # Verify ownership via trip
    await verify_trip_access(existing_list.trip_id, current_user, db)

    # Update fields
    existing_list.title = place_list.title
    existing_list.icon = place_list.icon
    existing_list.color = place_list.color
    existing_list.is_collapsed = place_list.is_collapsed
    existing_list.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(existing_list)

    # Get place count
    result = await db.execute(
        select(func.count(Place.id))
        .where(Place.list_id == list_id)
    )
    place_count = result.scalar() or 0

    logger.info("place_list_updated", list_id=list_id, trip_id=existing_list.trip_id, user_id=current_user.id)

    return PlaceListResponse(
        id=existing_list.id,
        trip_id=existing_list.trip_id,
        title=existing_list.title,
        icon=existing_list.icon,
        color=existing_list.color,
        is_collapsed=existing_list.is_collapsed,
        place_count=place_count,
        created_at=existing_list.created_at
    )


@router.delete("/lists/{list_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_place_list(
    request: Request,
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a custom place list. Requires authentication and trip ownership."""
    # Get existing list
    result = await db.execute(select(PlaceList).where(PlaceList.id == list_id))
    existing_list = result.scalar_one_or_none()

    if not existing_list:
        raise HTTPException(status_code=404, detail="Place list not found")

    # Verify ownership via trip
    await verify_trip_access(existing_list.trip_id, current_user, db)

    # Set list_id to NULL for all places in this list (handled by foreign key ON DELETE SET NULL)
    await db.delete(existing_list)
    await db.commit()

    logger.info("place_list_deleted", list_id=list_id, trip_id=existing_list.trip_id, user_id=current_user.id)

    return None


@router.patch("/lists/{list_id}/toggle-collapse")
@limiter.limit("60/minute")
async def toggle_list_collapse(
    request: Request,
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Toggle collapse state of a place list. Requires authentication and trip ownership."""
    # Get existing list
    result = await db.execute(select(PlaceList).where(PlaceList.id == list_id))
    existing_list = result.scalar_one_or_none()

    if not existing_list:
        raise HTTPException(status_code=404, detail="Place list not found")

    # Verify ownership via trip
    await verify_trip_access(existing_list.trip_id, current_user, db)

    # Toggle collapse state
    existing_list.is_collapsed = not existing_list.is_collapsed
    existing_list.updated_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info("place_list_toggled", list_id=list_id, is_collapsed=existing_list.is_collapsed, user_id=current_user.id)

    return {"success": True, "is_collapsed": existing_list.is_collapsed}


# ============ Guide Import Models ============
class GuideUrlRequest(BaseModel):
    url: str = Field(..., example="https://www.tripadvisor.com/Attractions-g187467-Activities-La_Palma_Canary_Islands.html")
    destination: str = Field(..., example="La Palma")


class GuideSearchRequest(BaseModel):
    destination: str = Field(..., example="La Palma", description="Destination to search for (e.g., 'Paris', 'Tokyo', 'Bali')")


class ExtractedPlace(BaseModel):
    name: str
    category: str
    description: Optional[str]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


class GuideParseResponse(BaseModel):
    success: bool
    url: Optional[str] = None
    destination: Optional[str] = None
    places_found: int = 0
    places: List[ExtractedPlace] = []
    error: Optional[str] = None


class GuideSearchResponse(BaseModel):
    success: bool
    destination: str
    sources_searched: List[str] = []
    places_found: int = 0
    places: List[ExtractedPlace] = []
    errors: Optional[List[str]] = None


class BulkPlaceImport(BaseModel):
    places: List[PlaceCreate]


# Guide Import Endpoints
@router.post("/{trip_id}/search-guides", response_model=GuideSearchResponse)
async def search_guides_auto(
    trip_id: int,
    request: GuideSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    AI-powered destination place discovery

    Simply provide a destination name (e.g., "Paris", "Bali", "Tokyo") and
    this endpoint will use AI to:
    1. Generate top attractions, restaurants, and points of interest
    2. Include descriptions, categories, and estimated costs
    3. Fetch real photos from Pexels
    4. Return a curated list ready to import

    This is the easiest and most reliable way to find places for your trip!
    """
    # Verify trip exists
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # If authenticated, verify ownership
    if current_user and trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get user's AI service (needed for place discovery)
    from routes.auth import get_current_active_user
    from routes.ai import get_user_ai_service
    from services.pexels_service import get_place_photo
    import json
    import asyncio

    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required for AI features")

    ai_service = get_user_ai_service(current_user)

    try:
        # Use AI to generate places for the destination
        prompt = f"""Du bist ein Reiseexperte. Erstelle eine Liste der besten Orte und Attraktionen für {request.destination}.

Gib eine umfassende Liste mit verschiedenen Kategorien:
- Top-Sehenswürdigkeiten (5-7)
- Beliebte Restaurants (3-4)
- Aussichtspunkte (2-3)
- Parks und Natur (2-3)
- Museen oder kulturelle Orte (2-3)
- Strände (falls zutreffend) (2-3)

Antworte AUSSCHLIESSLICH mit einem validen JSON-Array in diesem Format:
[
  {{
    "name": "Name des Ortes",
    "category": "attraction|restaurant|beach|viewpoint|museum|park|shopping|nightlife|other",
    "description": "Ansprechende Beschreibung (2-3 Sätze)",
    "address": "Vollständige Adresse des Ortes",
    "latitude": 28.6835,
    "longitude": -17.7649,
    "estimated_cost": 15,
    "image_search": "Englischer Suchbegriff für Bilder (2-3 Wörter)"
  }}
]

Wichtig:
- Maximal 20-25 Orte
- Deutsche Sprache für name, description
- image_search in ENGLISCH für Bildsuche
- **ECHTE GPS-Koordinaten (latitude, longitude) für jeden Ort - NICHT 0,0!**
- Vollständige Adressen angeben
- Nur JSON zurückgeben, kein zusätzlicher Text
- Verschiedene Kategorien mischen
- Reale, existierende Orte mit korrekten Koordinaten"""

        response = await ai_service.chat(
            user_message=prompt,
            context={"destination": request.destination}
        )

        # Parse AI response - handle markdown code blocks and extra text
        response_cleaned = response.strip()

        # Remove markdown code blocks if present
        if response_cleaned.startswith("```"):
            # Extract content between ``` markers
            lines = response_cleaned.split('\n')
            # Remove first line (```json or just ```)
            lines = lines[1:]
            # Find closing ```
            closing_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    closing_idx = i
                    break
            if closing_idx >= 0:
                lines = lines[:closing_idx]
            response_cleaned = '\n'.join(lines).strip()

        # Find JSON array in response (handle cases where AI adds text before/after)
        json_start = response_cleaned.find('[')
        json_end = response_cleaned.rfind(']')

        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON array found in AI response")

        json_str = response_cleaned[json_start:json_end+1]
        places_data = json.loads(json_str)

        # Fetch photos in parallel
        photo_tasks = [
            get_place_photo(
                place_name=place.get('image_search', place['name']),
                category=place.get('category', 'other'),
                destination=request.destination
            )
            for place in places_data
        ]
        photo_urls = await asyncio.gather(*photo_tasks)

        # Build ExtractedPlace objects
        places = []
        for i, place_data in enumerate(places_data):
            places.append(ExtractedPlace(
                name=place_data['name'],
                description=place_data.get('description', ''),
                address=place_data.get('address'),
                latitude=place_data.get('latitude', 0),
                longitude=place_data.get('longitude', 0),
                category=place_data.get('category', 'other')
            ))

        return GuideSearchResponse(
            success=True,
            destination=request.destination,
            places_found=len(places),
            places=places,
            sources_searched=["AI-powered discovery"]
        )

    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error for {request.destination}: {str(e)}")
        print(f"   AI Response (first 500 chars): {response[:500] if 'response' in locals() else 'N/A'}")
        return GuideSearchResponse(
            success=False,
            destination=request.destination,
            error=f"AI returned invalid JSON: {str(e)}",
            places_found=0,
            places=[]
        )
    except Exception as e:
        print(f"❌ Error in search-guides for {request.destination}: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return GuideSearchResponse(
            success=False,
            destination=request.destination,
            error=f"{type(e).__name__}: {str(e)}",
            places_found=0,
            places=[]
        )


@router.post("/{trip_id}/import-from-guide", response_model=GuideParseResponse)
async def parse_guide_url(
    trip_id: int,
    request: GuideUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Parse a travel guide URL and extract places

    Supports URLs from:
    - TripAdvisor
    - Lonely Planet
    - Google Travel
    - Wanderlog
    - And other travel guide sites

    Uses AI to intelligently extract places from the page content.
    """
    # Verify trip exists
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # If authenticated, verify ownership
    if current_user and trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        result = await guide_parser_service.parse_guide_url(
            url=request.url,
            destination=request.destination
        )

        return GuideParseResponse(**result)

    except Exception as e:
        return GuideParseResponse(
            success=False,
            error=str(e),
            places_found=0,
            places=[]
        )


@router.post("/{trip_id}/import-places-bulk", response_model=List[PlaceResponse])
async def import_places_bulk(
    trip_id: int,
    import_data: BulkPlaceImport,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Import multiple places at once

    Used after parsing a guide URL to add selected places to the trip.
    """
    # Verify trip exists
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # If authenticated, verify ownership
    if current_user and trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get current max order
    result = await db.execute(
        select(func.max(Place.order))
        .where(Place.trip_id == trip_id)
    )
    max_order = result.scalar() or 0

    imported_places = []

    for idx, place_data in enumerate(import_data.places):
        # Geocode if coordinates are missing
        latitude, longitude = await geocode_if_missing(
            name=place_data.name,
            latitude=place_data.latitude or 0.0,
            longitude=place_data.longitude or 0.0,
            address=place_data.address,
            destination=trip.destination if hasattr(trip, 'destination') else None
        )

        new_place = Place(
            trip_id=trip_id,
            name=place_data.name,
            description=place_data.description,
            address=place_data.address,
            latitude=latitude,
            longitude=longitude,
            category=place_data.category,
            list_id=place_data.list_id,
            visit_date=place_data.visit_date,
            visited=place_data.visited,
            website=place_data.website,
            phone=place_data.phone,
            cost=place_data.cost,
            currency=place_data.currency,
            rating=place_data.rating,
            notes=place_data.notes,
            photos=place_data.photos,
            order=max_order + idx + 1
        )

        db.add(new_place)
        imported_places.append(new_place)

    await db.commit()

    # Refresh all places
    for place in imported_places:
        await db.refresh(place)

    return imported_places


# ==================== PHOTO UPLOAD ENDPOINTS ====================

@router.post("/places/{place_id}/upload-photo")
@limiter.limit("10/minute")
async def upload_place_photo(
    request: Request,
    place_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a photo to a place.
    Requires authentication and trip ownership. Validates file content for security.
    """
    # Get place
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Verify trip ownership
    trip = await verify_trip_access(place.trip_id, current_user, db)

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # CRITICAL: Validate file type by content (security check)
    if not validate_photo_type(content, file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only images allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    file_ext = file.filename.split('.')[-1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Add photo to place
    photo_url = f"/uploads/places/{unique_filename}"
    if place.photos is None:
        place.photos = []
    place.photos = place.photos + [photo_url]  # Create new list for SQLAlchemy change tracking
    place.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(place)

    logger.info("place_photo_uploaded", place_id=place_id, filename=unique_filename, user_id=current_user.id)

    return {
        "message": "Photo uploaded successfully",
        "photo_url": photo_url,
        "place": place
    }


@router.delete("/places/{place_id}/photo")
@limiter.limit("20/minute")
async def delete_place_photo(
    request: Request,
    place_id: int,
    photo_url: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a photo from a place"""
    # Get place
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()

    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Verify trip ownership
    trip = await verify_trip_access(place.trip_id, current_user, db)

    # Remove photo from list
    if place.photos and photo_url in place.photos:
        place.photos = [p for p in place.photos if p != photo_url]
        place.updated_at = datetime.now(timezone.utc)

        # Delete physical file
        try:
            filename = photo_url.split('/')[-1]
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning("failed_to_delete_file", error=str(e), photo_url=photo_url)

        await db.commit()
        await db.refresh(place)

        logger.info("place_photo_deleted", place_id=place_id, photo_url=photo_url, user_id=current_user.id)

        return {"message": "Photo deleted successfully", "place": place}
    else:
        raise HTTPException(status_code=404, detail="Photo not found in place")

