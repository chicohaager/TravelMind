"""
Claude AI Service
Integration with Anthropic Claude API for travel assistance
"""

import os
import json
from typing import Optional, Dict, Any, List
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class ClaudeService:
    """Service for interacting with Claude API"""

    def __init__(self):
        self.api_key = os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")

        self.client = Anthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))

    async def suggest_destinations(
        self,
        interests: List[str],
        duration: int,
        budget: Optional[str] = None,
        season: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate destination suggestions based on user preferences

        Args:
            interests: List of interests (e.g., ["nature", "culture", "food"])
            duration: Trip duration in days
            budget: Budget level (low, medium, high)
            season: Preferred season

        Returns:
            Dict with destination suggestions
        """
        prompt = f"""Du bist ein erfahrener Reiseplaner. Empfehle 5 passende Reiseziele basierend auf:

Interessen: {', '.join(interests)}
Dauer: {duration} Tage
{f"Budget: {budget}" if budget else ""}
{f"Jahreszeit: {season}" if season else ""}

Gib für jedes Ziel:
- Name und Land
- Warum es passt (2-3 Sätze)
- Beste Reisezeit
- Geschätztes Budget pro Tag
- Top 3 Aktivitäten

Ausgabe als JSON:
{{
    "destinations": [
        {{
            "name": "...",
            "country": "...",
            "reason": "...",
            "best_time": "...",
            "daily_budget": "...",
            "activities": ["...", "...", "..."],
            "coordinates": {{"lat": 0.0, "lng": 0.0}}
        }}
    ]
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Try to extract JSON from response
        try:
            # Find JSON in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_content = content[start:end]
                return json.loads(json_content)
            else:
                return {"destinations": [], "raw_response": content}
        except json.JSONDecodeError:
            return {"destinations": [], "raw_response": content}

    async def plan_trip(
        self,
        destination: str,
        duration: int,
        interests: List[str],
        accommodation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed trip itinerary

        Args:
            destination: Destination city/region
            duration: Trip duration in days
            interests: User interests
            accommodation_type: Type of accommodation preference

        Returns:
            Detailed day-by-day itinerary
        """
        prompt = f"""Du bist ein erfahrener Reiseplaner. Erstelle einen detaillierten {duration}-tägigen Reiseplan für {destination}.

Interessen: {', '.join(interests)}
{f"Unterkunft: {accommodation_type}" if accommodation_type else ""}

Erstelle für jeden Tag:
- Morgen, Mittag, Abend Aktivitäten
- Empfohlene Restaurants/Cafés
- Geschätzte Kosten
- Praktische Tipps (Transport, Tickets, etc.)

Füge hinzu:
- Geheimtipps abseits der Touristenpfade
- Lokale Spezialitäten zum Probieren
- Wichtige praktische Informationen

Ausgabe als strukturiertes JSON:
{{
    "trip_overview": {{
        "destination": "...",
        "duration": {duration},
        "best_for": ["..."]
    }},
    "days": [
        {{
            "day": 1,
            "theme": "...",
            "morning": {{"activity": "...", "location": "...", "cost": "..."}},
            "afternoon": {{"activity": "...", "location": "...", "cost": "..."}},
            "evening": {{"activity": "...", "location": "...", "cost": "..."}},
            "meals": ["...", "..."],
            "tips": "..."
        }}
    ],
    "local_tips": ["...", "..."],
    "food_recommendations": ["...", "..."],
    "total_estimated_cost": "..."
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_content = content[start:end]
                return json.loads(json_content)
            else:
                return {"days": [], "raw_response": content}
        except json.JSONDecodeError:
            return {"days": [], "raw_response": content}

    async def describe_destination(self, destination: str) -> str:
        """
        Generate a poetic, atmospheric description of a destination

        Args:
            destination: Destination name

        Returns:
            Markdown-formatted description
        """
        prompt = f"""Erstelle eine poetische, aber informative Beschreibung des Reiseziels {destination}.

Betone:
- Atmosphäre und Stimmung
- Kultur und Geschichte
- Natur und Landschaft
- Besondere Charakteristika

Stil: Inspirierend, reiselustig, aber nicht übertrieben
Länge: Maximal 300 Wörter
Ausgabe: Markdown-formatiert mit Absätzen"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    async def chat(
        self,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Chat with Claude about travel topics

        Args:
            user_message: User's question or message
            context: Optional context (previous messages in conversation)

        Returns:
            Claude's response
        """
        system_prompt = """Du bist ein lokaler Reiseexperte und beantwortest Fragen direkt und spezifisch.

WICHTIG:
- Beantworte die Frage DIREKT und KONKRET
- Gib SPEZIFISCHE Empfehlungen mit NAMEN von Orten
- Keine generischen Tipps wie "recherchiere die Kultur"
- Fokussiere dich auf die EXAKTE Frage
- Bei Fotospots: Gib konkrete Orte mit GPS-Koordinaten
- Bei Restaurants: Nenne konkrete Namen und Spezialitäten
- Bei Aktivitäten: Nenne konkrete Sehenswürdigkeiten

Beispiel GUTE Antwort:
"Für Sonnenaufgänge auf La Palma empfehle ich:
1. **Roque de los Muchachos** (28.7577°N, 17.8815°W) - Höchster Punkt, spektakulärer Blick über Wolken
2. **Mirador del Time** - Perfekt für Sonnenuntergänge über dem Meer
3. **Los Cancajos Beach** - Strandsonnenaufgänge mit Palmen"

Beispiel SCHLECHTE Antwort:
"Recherchiere die lokale Kultur und plane flexible Tage..."

Antworte immer in natürlichem Deutsch, strukturiert und hilfreich."""

        # Build messages array with conversation history
        messages = []

        # Add conversation history if provided
        if context and len(context) > 0:
            for msg in context:
                # Ensure msg is a dictionary
                if isinstance(msg, dict):
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

    async def get_local_tips(self, destination: str, category: str = "all") -> List[Dict[str, str]]:
        """
        Get local tips and hidden gems

        Args:
            destination: Destination name
            category: Category (restaurants, sights, activities, nightlife, all)

        Returns:
            List of tips with details
        """
        categories_text = {
            "restaurants": "Restaurants und Cafés",
            "sights": "Sehenswürdigkeiten",
            "activities": "Aktivitäten",
            "nightlife": "Nachtleben",
            "all": "alle Kategorien"
        }

        prompt = f"""Liste 10 Geheimtipps für {destination} auf, Kategorie: {categories_text.get(category, 'alle')}.

Fokus auf:
- Authentische, lokale Orte
- Abseits der Touristenpfade
- Von Einheimischen geschätzt
- Besondere Atmosphäre

Ausgabe als JSON Array:
[
    {{
        "name": "...",
        "category": "...",
        "description": "...",
        "why_special": "...",
        "location": "...",
        "coordinates": {{"lat": 0.0, "lng": 0.0}},
        "insider_tip": "..."
    }}
]"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                json_content = content[start:end]
                return json.loads(json_content)
            else:
                return []
        except json.JSONDecodeError:
            return []


# Singleton instance
claude_service = ClaudeService()
