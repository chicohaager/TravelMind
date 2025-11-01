"""
Geocoding utility using OpenStreetMap Nominatim API
Free geocoding service - no API key required
"""

import httpx
import asyncio
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

# Nominatim API configuration
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TravelMind/1.0 (self-hosted travel planning app)"
RATE_LIMIT_DELAY = 1.0  # Nominatim requires 1 request per second max


async def geocode_location(
    name: str,
    address: Optional[str] = None,
    destination: Optional[str] = None
) -> Optional[Tuple[float, float]]:
    """
    Geocode a location using OpenStreetMap Nominatim API

    Args:
        name: Name of the place (e.g., "Eiffel Tower")
        address: Optional full address
        destination: Optional destination/city (e.g., "Paris")

    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    # Build search query - prioritize full address if available
    if address:
        query = address
    else:
        query = name
        if destination:
            query = f"{name}, {destination}"

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }

    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(NOMINATIM_URL, params=params, headers=headers)
            response.raise_for_status()

            results = response.json()

            if results and len(results) > 0:
                result = results[0]
                lat = float(result["lat"])
                lon = float(result["lon"])

                logger.info(
                    "geocoded_location",
                    query=query,
                    latitude=lat,
                    longitude=lon,
                    display_name=result.get("display_name")
                )

                # Respect rate limit
                await asyncio.sleep(RATE_LIMIT_DELAY)

                return (lat, lon)
            else:
                logger.warning("geocoding_no_results", query=query)
                return None

    except httpx.HTTPError as e:
        logger.error("geocoding_http_error", query=query, error=str(e))
        return None
    except Exception as e:
        logger.error("geocoding_error", query=query, error=str(e), error_type=type(e).__name__)
        return None


async def geocode_if_missing(
    name: str,
    latitude: float,
    longitude: float,
    address: Optional[str] = None,
    destination: Optional[str] = None
) -> Tuple[float, float]:
    """
    Geocode location if coordinates are missing (0.0, 0.0)

    Returns:
        Tuple of (latitude, longitude) - original if valid, geocoded if missing
    """
    # Check if coordinates are missing (0,0 or very close to it)
    if abs(latitude) < 0.001 and abs(longitude) < 0.001:
        logger.info("geocoding_missing_coords", name=name, address=address)

        coords = await geocode_location(name, address, destination)

        if coords:
            return coords
        else:
            logger.warning("geocoding_failed_using_default", name=name)
            # Return original coordinates even if geocoding failed
            return (latitude, longitude)

    # Coordinates already valid
    return (latitude, longitude)


async def batch_geocode_places(places: list, destination: Optional[str] = None) -> list:
    """
    Batch geocode multiple places with rate limiting

    Args:
        places: List of place dictionaries with 'name', 'latitude', 'longitude', 'address'
        destination: Optional destination context

    Returns:
        Updated list of places with geocoded coordinates
    """
    updated_places = []

    for place in places:
        name = place.get('name', '')
        lat = place.get('latitude', 0.0)
        lon = place.get('longitude', 0.0)
        address = place.get('address')

        # Geocode if needed
        new_lat, new_lon = await geocode_if_missing(name, lat, lon, address, destination)

        # Update place with new coordinates
        updated_place = place.copy()
        updated_place['latitude'] = new_lat
        updated_place['longitude'] = new_lon

        updated_places.append(updated_place)

    return updated_places
