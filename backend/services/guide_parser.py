"""
Travel Guide Parser Service
Extract places from travel guide URLs (TripAdvisor, Lonely Planet, etc.)
"""

import httpx
import re
import json
import asyncio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from anthropic import Anthropic
import os
from urllib.parse import quote


class GuideParserService:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.claude_client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    async def fetch_url_content(self, url: str) -> Optional[str]:
        """
        Fetch content from a URL

        Args:
            url: The URL to fetch

        Returns:
            HTML content as string or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return None

    def extract_text_from_html(self, html: str) -> str:
        """
        Extract readable text from HTML

        Args:
            html: HTML content

        Returns:
            Plain text content
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            print(f"Error extracting text from HTML: {e}")
            return ""

    async def extract_places_with_ai(self, text: str, destination: str) -> List[Dict]:
        """
        Use Claude AI to extract places from text

        Args:
            text: Text content to analyze
            destination: Destination name for context

        Returns:
            List of extracted places with details
        """
        # Truncate text if too long (Claude has token limits)
        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        prompt = f"""You are analyzing a travel guide about {destination}.

Extract all mentioned places of interest (attractions, restaurants, hotels, beaches, viewpoints, etc.) from the following text.

For each place, extract:
- name: The place name
- category: One of: restaurant, attraction, beach, hotel, viewpoint, museum, park, shopping, nightlife, other
- description: A brief description (1-2 sentences)
- address: If mentioned (or null)
- coordinates: If mentioned as lat/long (or null)

Return ONLY a valid JSON array with this structure:
[
  {{
    "name": "Place Name",
    "category": "attraction",
    "description": "Brief description",
    "address": "Address if available",
    "latitude": null,
    "longitude": null
  }}
]

Important:
- Only extract real places, not general references
- Skip navigation elements, ads, and metadata
- Keep descriptions concise
- Return ONLY the JSON array, no other text

Text to analyze:
{text}
"""

        try:
            message = self.claude_client.messages.create(
                model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse Claude's response
            response_text = message.content[0].text

            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                places = json.loads(json_match.group(0))
                return places
            else:
                print("No JSON found in Claude response")
                return []

        except Exception as e:
            print(f"Error extracting places with AI: {e}")
            return []

    async def parse_guide_url(self, url: str, destination: str) -> Dict:
        """
        Parse a travel guide URL and extract places

        Args:
            url: URL to parse
            destination: Destination name for context

        Returns:
            Dictionary with parsed results
        """
        # Fetch content
        html = await self.fetch_url_content(url)
        if not html:
            return {
                "success": False,
                "error": "Failed to fetch URL",
                "places": []
            }

        # Extract text
        text = self.extract_text_from_html(html)
        if not text:
            return {
                "success": False,
                "error": "Failed to extract text from page",
                "places": []
            }

        # Extract places with AI
        places = await self.extract_places_with_ai(text, destination)

        return {
            "success": True,
            "url": url,
            "destination": destination,
            "places_found": len(places),
            "places": places
        }

    def detect_guide_type(self, url: str) -> Optional[str]:
        """
        Detect the type of travel guide from URL

        Args:
            url: URL to analyze

        Returns:
            Guide type (tripadvisor, lonelyplanet, etc.) or None
        """
        url_lower = url.lower()

        if "tripadvisor" in url_lower:
            return "tripadvisor"
        elif "lonelyplanet" in url_lower:
            return "lonelyplanet"
        elif "timeout.com" in url_lower:
            return "timeout"
        elif "wanderlog" in url_lower:
            return "wanderlog"
        elif "google.com/travel" in url_lower:
            return "google_travel"
        else:
            return "generic"

    def generate_guide_urls(self, destination: str) -> List[Dict[str, str]]:
        """
        Generate URLs for various travel guide sources for a destination

        Args:
            destination: Name of the destination

        Returns:
            List of dictionaries with 'source' and 'url' keys
        """
        # Normalize destination for URLs
        dest_search = quote(destination)

        # Common destination mappings for TripAdvisor
        # This is a simple approach - for production, you'd want a more comprehensive mapping
        tripadvisor_mapping = {
            "la palma": "https://www.tripadvisor.com/Attractions-g187467-Activities-La_Palma_Canary_Islands.html",
            "paris": "https://www.tripadvisor.com/Attractions-g187147-Activities-Paris_Ile_de_France.html",
            "tokyo": "https://www.tripadvisor.com/Attractions-g298184-Activities-Tokyo_Tokyo_Prefecture_Kanto.html",
            "bali": "https://www.tripadvisor.com/Attractions-g294226-Activities-Bali.html",
            "barcelona": "https://www.tripadvisor.com/Attractions-g187497-Activities-Barcelona_Catalonia.html",
            "new york": "https://www.tripadvisor.com/Attractions-g60763-Activities-New_York_City_New_York.html",
            "london": "https://www.tripadvisor.com/Attractions-g186338-Activities-London_England.html",
        }

        # Try to get a direct URL, otherwise use search
        dest_lower = destination.lower().strip()
        tripadvisor_url = tripadvisor_mapping.get(dest_lower,
            f"https://www.tripadvisor.com/Search?q={dest_search}")

        urls = [
            {
                "source": "TripAdvisor",
                "url": tripadvisor_url
            }
        ]

        return urls

    async def search_single_source(self, source: str, url: str, destination: str) -> Dict:
        """
        Search a single guide source

        Args:
            source: Name of the source (e.g., "TripAdvisor")
            url: URL to search
            destination: Destination name

        Returns:
            Dictionary with source and extracted places
        """
        try:
            result = await self.parse_guide_url(url, destination)
            result["source"] = source
            return result
        except Exception as e:
            print(f"Error searching {source}: {e}")
            return {
                "source": source,
                "success": False,
                "error": str(e),
                "places": []
            }

    def deduplicate_places(self, all_places: List[Dict]) -> List[Dict]:
        """
        Remove duplicate places based on name similarity

        Args:
            all_places: List of all places from various sources

        Returns:
            Deduplicated list of places
        """
        seen = {}
        unique_places = []

        for place in all_places:
            name_normalized = place["name"].lower().strip()

            # Simple deduplication by normalized name
            if name_normalized not in seen:
                seen[name_normalized] = True
                unique_places.append(place)

        return unique_places

    async def search_guides_by_destination(self, destination: str, max_sources: int = 1) -> Dict:
        """
        Automatically search multiple travel guide sources for a destination

        Args:
            destination: Name of the destination to search
            max_sources: Maximum number of sources to search (default 2)

        Returns:
            Dictionary with combined results from all sources
        """
        # Generate URLs for various sources
        guide_urls = self.generate_guide_urls(destination)[:max_sources]

        # Search all sources in parallel
        tasks = [
            self.search_single_source(guide["source"], guide["url"], destination)
            for guide in guide_urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all places
        all_places = []
        sources_searched = []
        errors = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                continue

            if result.get("success"):
                all_places.extend(result.get("places", []))
                sources_searched.append(result.get("source", "Unknown"))
            else:
                errors.append(f"{result.get('source', 'Unknown')}: {result.get('error', 'Unknown error')}")

        # Deduplicate places
        unique_places = self.deduplicate_places(all_places)

        return {
            "success": len(unique_places) > 0,
            "destination": destination,
            "sources_searched": sources_searched,
            "places_found": len(unique_places),
            "places": unique_places,
            "errors": errors if errors else None
        }


# Singleton instance
guide_parser_service = GuideParserService()
