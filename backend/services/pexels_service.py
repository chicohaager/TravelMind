"""
Pexels Photo API Service
Fetch high-quality photos for places and recommendations
"""

import os
import aiohttp
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_API_URL = "https://api.pexels.com/v1/search"


async def search_photo(query: str, per_page: int = 1) -> Optional[str]:
    """
    Search for a photo on Pexels and return the image URL

    Args:
        query: Search query (e.g., "Miniatur Wunderland Hamburg")
        per_page: Number of results to return (default 1)

    Returns:
        URL of the medium-sized photo, or None if not found
    """
    if not PEXELS_API_KEY:
        print("⚠️  Pexels API key not configured")
        return None

    try:
        headers = {
            "Authorization": PEXELS_API_KEY
        }

        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "landscape"  # Better for cards
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(PEXELS_API_URL, headers=headers, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("photos") and len(data["photos"]) > 0:
                        photo = data["photos"][0]
                        # Use medium size (good balance between quality and loading speed)
                        return photo["src"]["medium"]

                    # No photos found
                    return None
                else:
                    print(f"⚠️  Pexels API error: {response.status}")
                    return None

    except Exception as e:
        print(f"⚠️  Error fetching photo from Pexels: {e}")
        return None


async def get_place_photo(place_name: str, category: str, destination: str = "") -> str:
    """
    Get a photo for a place based on its name, category, and destination

    Args:
        place_name: Name of the place or AI-generated search term (e.g., "la palma beach sunset")
        category: Category of the place (e.g., "attraction", "restaurant")
        destination: Optional destination context (e.g., "La Palma")

    Returns:
        Photo URL (from Pexels or fallback to placeholder)
    """
    # Build search query - prioritize AI-generated search terms
    queries_to_try = []

    # Check if place_name looks like an AI search term (English, multiple words, lowercase)
    is_search_term = ' ' in place_name and place_name.islower()

    if is_search_term:
        # 1. If it's already a good search term, use it directly
        queries_to_try.append(place_name)
        # 2. Try with destination as backup
        if destination:
            queries_to_try.append(f"{place_name} {destination}")
    else:
        # Traditional search: specific place name
        # 1. Try full name + destination
        if destination:
            queries_to_try.append(f"{place_name} {destination}")
        # 2. Try just the name
        queries_to_try.append(place_name)

    # 3. Try category + destination as final fallback
    if destination and category:
        category_keywords = {
            "restaurant": "restaurant food cuisine",
            "attraction": "tourist landmark sightseeing",
            "beach": "beach ocean coastline",
            "hotel": "hotel resort accommodation",
            "viewpoint": "scenic viewpoint landscape",
            "museum": "museum art gallery",
            "park": "park nature garden",
            "shopping": "shopping market store",
            "nightlife": "nightlife bar club",
            "other": "travel destination"
        }
        category_query = category_keywords.get(category, "travel")
        queries_to_try.append(f"{destination} {category_query}")

    # Try each query until we find a photo
    for query in queries_to_try:
        photo_url = await search_photo(query)
        if photo_url:
            print(f"✓ Pexels: '{place_name}' → query: '{query}'")
            return photo_url

    # Fallback to placeholder if no Pexels photo found
    print(f"⚠️  Pexels: No photo for '{place_name}', using placeholder")
    seed = sum(ord(char) for char in place_name)
    image_id = 100 + (seed % 900)
    return f"https://picsum.photos/seed/{image_id}/800/600"
