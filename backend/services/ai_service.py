"""
Unified AI Service
Supports multiple AI providers: Claude (Anthropic), OpenAI, Gemini (Google), and Groq
"""

import json
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from anthropic import Anthropic
import openai
import google.generativeai as genai
from groq import Groq


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0
    ) -> str:
        """
        Send a chat message and get a response

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens in response
            temperature: Randomness (0.0 = deterministic, 1.0 = creative)

        Returns:
            AI response text
        """
        pass


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0
    ) -> str:
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Run synchronous API call in thread pool to avoid blocking event loop
        response = await asyncio.to_thread(self.client.messages.create, **kwargs)
        return response.content[0].text


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0
    ) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Run synchronous API call in thread pool to avoid blocking event loop
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return response.choices[0].message.content


class GeminiProvider(AIProvider):
    """Google Gemini provider"""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0
    ) -> str:
        # Gemini combines system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }

        # Run synchronous API call in thread pool to avoid blocking event loop
        response = await asyncio.to_thread(
            self.model.generate_content,
            full_prompt,
            generation_config=generation_config
        )

        return response.text


class GroqProvider(AIProvider):
    """Groq provider (fast, free inference with Llama models)"""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0
    ) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Run synchronous API call in thread pool to avoid blocking event loop
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return response.choices[0].message.content


class UnifiedAIService:
    """
    Unified service for AI operations across multiple providers
    Provides common methods for travel planning tasks
    """

    def __init__(self, provider: AIProvider):
        self.provider = provider

    async def suggest_destinations(
        self,
        interests: List[str],
        duration: int,
        budget: Optional[str] = None,
        season: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate destination suggestions based on user preferences"""
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

        response = await self.provider.chat(prompt, max_tokens=2048)

        # Try to extract JSON from response
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_content = response[start:end]
                return json.loads(json_content)
            else:
                return {"destinations": [], "raw_response": response}
        except json.JSONDecodeError:
            return {"destinations": [], "raw_response": response}

    async def plan_trip(
        self,
        destination: str,
        duration: int,
        interests: List[str],
        accommodation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a detailed trip itinerary"""
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

        response = await self.provider.chat(prompt, max_tokens=2048)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_content = response[start:end]
                return json.loads(json_content)
            else:
                return {"days": [], "raw_response": response}
        except json.JSONDecodeError:
            return {"days": [], "raw_response": response}

    async def describe_destination(self, destination: str) -> str:
        """Generate a poetic, atmospheric description of a destination"""
        prompt = f"""Erstelle eine poetische, aber informative Beschreibung des Reiseziels {destination}.

Betone:
- Atmosphäre und Stimmung
- Kultur und Geschichte
- Natur und Landschaft
- Besondere Charakteristika

Stil: Inspirierend, reiselustig, aber nicht übertrieben
Länge: Maximal 300 Wörter
Ausgabe: Markdown-formatiert mit Absätzen"""

        return await self.provider.chat(prompt, max_tokens=1024)

    async def chat(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Chat with AI about travel topics"""
        system_prompt = """Du bist ein lokaler Reiseexperte und beantwortest Fragen direkt und spezifisch.

WICHTIG:
- Beantworte die Frage DIREKT und KONKRET
- Gib SPEZIFISCHE Empfehlungen mit NAMEN von Orten
- Keine generischen Tipps wie "recherchiere die Kultur"
- Fokussiere dich auf die EXAKTE Frage
- Bei Fotospots: Gib konkrete Orte mit GPS-Koordinaten
- Bei Restaurants: Nenne konkrete Namen und Spezialitäten
- Bei Aktivitäten: Nenne konkrete Sehenswürdigkeiten

Antworte immer in natürlichem Deutsch, strukturiert und hilfreich."""

        return await self.provider.chat(user_message, system_prompt=system_prompt, max_tokens=2048)

    async def get_local_tips(self, destination: str, category: str = "all") -> List[Dict[str, str]]:
        """Get local tips and hidden gems"""
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

        response = await self.provider.chat(prompt, max_tokens=2048)

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                json_content = response[start:end]
                return json.loads(json_content)
            else:
                return []
        except json.JSONDecodeError:
            return []


def create_ai_service(provider_name: str, api_key: str) -> UnifiedAIService:
    """
    Factory function to create an AI service with the specified provider

    Args:
        provider_name: "claude", "openai", "gemini", or "groq"
        api_key: API key for the provider

    Returns:
        UnifiedAIService instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_name = provider_name.upper()

    if provider_name == "CLAUDE":
        provider = ClaudeProvider(api_key)
    elif provider_name == "OPENAI":
        provider = OpenAIProvider(api_key)
    elif provider_name == "GEMINI":
        provider = GeminiProvider(api_key)
    elif provider_name == "GROQ":
        provider = GroqProvider(api_key)
    else:
        raise ValueError(f"Unsupported AI provider: {provider_name}")

    return UnifiedAIService(provider)
