"""
Geocoding Service
Convert location names to coordinates using Nominatim (OpenStreetMap)
"""

import httpx
from typing import Optional, Dict, Any
import asyncio


class GeocodingService:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.user_agent = "TravelMind/1.0"

    async def geocode(self, location: str) -> Optional[Dict[str, Any]]:
        """
        Convert a location name to coordinates

        Args:
            location: Location name (e.g., "Barcelona", "Rome, Italy")

        Returns:
            Dict with latitude, longitude, and display_name, or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": location,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1
                    },
                    headers={
                        "User-Agent": self.user_agent
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                data = response.json()

                if not data:
                    return None

                result = data[0]
                return {
                    "latitude": float(result["lat"]),
                    "longitude": float(result["lon"]),
                    "display_name": result.get("display_name", location),
                    "type": result.get("type"),
                    "importance": result.get("importance", 0)
                }

        except httpx.HTTPError as e:
            print(f"Geocoding error for '{location}': {e}")
            return None
        except Exception as e:
            print(f"Unexpected geocoding error: {e}")
            return None

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to a location name

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            Location name string, or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/reverse",
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "format": "json"
                    },
                    headers={
                        "User-Agent": self.user_agent
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                data = response.json()

                if "display_name" in data:
                    return data["display_name"]
                return None

        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return None


# Singleton instance
geocoding_service = GeocodingService()
