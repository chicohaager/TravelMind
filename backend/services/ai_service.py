"""
Unified AI Service
Supports multiple AI providers: Claude (Anthropic), OpenAI, Gemini (Google), and Groq
"""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import openai
from anthropic import Anthropic
from groq import Groq
from utils.ki_antwort import nur_objekte, parse_ai_json

# ── Modell-IDs ──────────────────────────────────────────────────────────────
#
# Am 2026-08-25 gegen die Herstellerdokumentation geprueft, nicht aus dem
# Gedaechtnis. Stand davor und was die Doku sagte:
#
#   Claude  claude-sonnet-4-6                             -> legacy, aktuell claude-sonnet-5
#   OpenAI  gpt-5.4                                       -> nicht mehr gelistet
#   Gemini  gemini-3.5-flash                              -> gelistet, aber als legacy bezeichnet
#   Groq    meta-llama/llama-4-maverick-17b-128e-instruct -> UEBERHAUPT NICHT MEHR GELISTET
#
# Der letzte Fall ist der teure: Groq ist der Standardanbieter (kostenlos),
# und sein Modell gab es nicht mehr. Jede KI-Anfrage waere fehlgeschlagen.
#
# Deshalb stehen die IDs jetzt in der Umgebung: eine Modell-ID ist ein
# GEMESSENER WERT, kein Vertrag. Der Hersteller nimmt sie aus dem Angebot,
# wann er will, und dann darf die Reparatur kein neues Image brauchen.
STANDARD_MODELLE = {
    "CLAUDE_MODEL": "claude-sonnet-5",
    "OPENAI_MODEL": "gpt-5.6-terra",
    "GEMINI_MODEL": "gemini-3.7-flash",
    "GROQ_MODEL": "llama-3.3-70b-versatile",
}


def modell_id(variable: str) -> str:
    """Die Modell-ID zur Laufzeit aufloesen, nicht beim Import.

    Beim Import gelesen wuerde eine Aenderung der Umgebung erst nach einem
    Neustart wirken — und in Tests braeuchte es ein `importlib.reload`, das
    die Klassenobjekte austauscht und damit jeden `isinstance`-Vergleich in
    anderen Dateien zerlegt (am 2026-08-25 genau so passiert: 5 fremde Tests
    fielen).
    """
    return os.getenv(variable) or STANDARD_MODELLE[variable]


def _abbruch_pruefen(anbieter: str, response, max_tokens: int) -> None:
    """Laut scheitern, wenn die Antwort am Token-Limit abgeschnitten wurde.

    OpenAI und Groq melden das als `finish_reason == "length"`. Ohne diese
    Pruefung geht der halbe Text weiter in den JSON-Parser, und dessen Meldung
    zeigt dann auf die Formatierung statt auf die Ursache — dieselbe Falle wie
    bei Claude (siehe `CLAUDE_DENK_RESERVE`).

    Defensiv per getattr: ein SDK-Sprung, der das Feld umbenennt, darf hier
    keinen Absturz erzeugen — dann greift die Pruefung eben nicht mehr, und
    das faellt im Test auf, nicht beim Nutzer.
    """
    wahl = next(iter(getattr(response, "choices", None) or []), None)
    if getattr(wahl, "finish_reason", None) == "length":
        raise RuntimeError(
            f"{anbieter}-Antwort am Token-Limit abgeschnitten (max_tokens={max_tokens}). "
            f"Weniger Ausgabe anfordern oder das Budget erhoehen."
        )


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    async def chat(
        self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048, temperature: float = 1.0
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


# Auf Claude begrenzt `max_tokens` DENKEN UND TEXT ZUSAMMEN — bei den anderen
# drei Anbietern nur den Text.
#
# Die aktuellen Claude-Modelle denken adaptiv, ohne dass man es einschaltet:
# laut Anbieter-Doku (geprueft 2026-08-26) heisst "`thinking` weglassen" bei
# claude-sonnet-5 nicht "kein Denken", sondern "adaptives Denken". Ein knappes
# Budget geht damit ganz an den Denk-Block, und der Textblock kommt gar nicht
# mehr — oder nur halb.
#
# Am 2026-08-26 in der Produktion gemessen (Backend-Protokoll, Benutzer 2,
# 09:37–09:38): drei verschiedene Fehlerbilder aus EINER Ursache, alle auf
# /api/ai/personalized-recommendations, alle mit max_tokens=2048:
#   RuntimeError    "keinen Textblock (Blockarten: ['thinking'])"
#                   -> die 2048 gingen restlos ans Denken
#   JSONDecodeError "Expecting property name … line 24 column 26"
#                   -> Text mitten im Array abgeschnitten
#   AttributeError  "'str' object has no attribute 'get'"
#                   -> abgeschnittenes Array, vom Notfall-Zweig als OBJEKT
#                      geparst; das Iterieren lieferte dann Schluessel (str)
#
# Der Aufrufer meint mit `max_tokens` den TEXT, den er braucht. Also legt
# dieser Anbieter das Denk-Budget obendrauf, statt es ihm wegzunehmen.
# Abgerechnet werden nur die tatsaechlich erzeugten Token — eine grosszuegige
# Reserve kostet nichts, wenn kurz gedacht wird.
CLAUDE_DENK_RESERVE = 8192


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: str, model: str = None):
        model = model or modell_id("CLAUDE_MODEL")
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.model_id = model

    async def chat(
        self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048, temperature: float = 1.0
    ) -> str:
        messages = [{"role": "user", "content": prompt}]

        # KEIN `temperature` hier.
        #
        # Der anthropic-SDK 1.0.0 nimmt es nicht mehr an — `Messages.create()`
        # wirft `TypeError: got an unexpected keyword argument 'temperature'`.
        # Am 2026-08-25 in der Produktion gemessen: JEDE Claude-Anfrage
        # scheiterte damit, seit der SDK-Sprung passiert ist. Aufgefallen ist
        # es erst, als der Fehlerpfad anfing zu protokollieren — vorher ging
        # die Meldung als "AI service error" an den Nutzer und niemand sah,
        # WAS fehlschlug.
        #
        # Der Parameter bleibt in der Signatur, weil die anderen drei Anbieter
        # ihn annehmen; hier wird er bewusst verworfen. `test_ai_service.py`
        # prueft, dass die uebergebenen Argumente zur INSTALLIERTEN Signatur
        # passen — damit faellt der naechste solche Sprung im Test auf.
        budget = max_tokens + CLAUDE_DENK_RESERVE
        kwargs = {"model": self.model, "max_tokens": budget, "messages": messages}

        if system_prompt:
            kwargs["system"] = system_prompt

        # Run synchronous API call in thread pool to avoid blocking event loop
        response = await asyncio.to_thread(self.client.messages.create, **kwargs)

        # Abgeschnitten? Dann LAUT scheitern, nicht halben Text weiterreichen.
        #
        # Ohne diese Zeile wandert eine abgeschnittene Antwort in den
        # JSON-Parser und scheitert dort mit einer Meldung ueber Anfuehrungs-
        # zeichen in Zeile 24 — die auf die Formatierung zeigt statt auf das
        # Token-Limit. Genau daran ist am 2026-08-26 eine Stunde verloren
        # gegangen: drei Fehlermeldungen, keine nannte die Ursache.
        if getattr(response, "stop_reason", None) == "max_tokens":
            erzeugt = getattr(getattr(response, "usage", None), "output_tokens", "?")
            raise RuntimeError(
                f"Claude-Antwort am Token-Limit abgeschnitten (max_tokens={budget}, "
                f"erzeugt={erzeugt}). Denk-Block und Text teilen sich dieses Budget — "
                f"CLAUDE_DENK_RESERVE erhoehen oder weniger Ausgabe anfordern."
            )

        # Den ERSTEN Textblock suchen, nicht `content[0]` annehmen.
        #
        # Die aktuellen Claude-Modelle denken adaptiv: die Antwort beginnt
        # dann mit einem `thinking`-Block, und der Text steht dahinter.
        # `content[0].text` gibt es in dem Fall nicht — am 2026-08-25 in der
        # Produktion gemessen, nachdem der Modellwechsel auf claude-sonnet-5
        # den vorigen Fehler (`temperature`) freigelegt hatte: die Anfrage
        # lief 20,9 s durch und scheiterte dann an dieser Zeile.
        text = next((getattr(b, "text", None) for b in (response.content or []) if getattr(b, "text", None)), None)
        if not text:
            arten = [getattr(b, "type", type(b).__name__) for b in (response.content or [])]
            raise RuntimeError(f"Claude lieferte keinen Textblock (Blockarten: {arten or 'keine'})")
        return text


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: str, model: str = None):
        model = model or modell_id("OPENAI_MODEL")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.model_id = model

    async def chat(
        self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048, temperature: float = 1.0
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
            # `max_tokens` ist laut OpenAI-Doku (geprueft 2026-08-25) zugunsten
            # von `max_completion_tokens` veraltet und mit den Reasoning-
            # Modellen nicht mehr vertraeglich.
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )

        _abbruch_pruefen("OpenAI", response, max_tokens)

        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("OpenAI returned an empty response")
        return response.choices[0].message.content


class GeminiProvider(AIProvider):
    """Google Gemini provider"""

    def __init__(self, api_key: str, model: str = None):
        model = model or modell_id("GEMINI_MODEL")
        genai.configure(api_key=api_key)
        # `self.model` ist hier ein SDK-Objekt, keine Zeichenkette. Ohne
        # `model_id` laesst sich die benutzte ID nirgends ablesen.
        self.model_id = model
        self.model = genai.GenerativeModel(model)

    async def chat(
        self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048, temperature: float = 1.0
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
            self.model.generate_content, full_prompt, generation_config=generation_config
        )

        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty or blocked response")
        return text


class GroqProvider(AIProvider):
    """Groq provider (fast, free inference with Llama models)"""

    def __init__(self, api_key: str, model: str = None):
        model = model or modell_id("GROQ_MODEL")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.model_id = model

    async def chat(
        self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048, temperature: float = 1.0
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
            temperature=temperature,
        )

        _abbruch_pruefen("Groq", response, max_tokens)

        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("Groq returned an empty response")
        return response.choices[0].message.content


class UnifiedAIService:
    """
    Unified service for AI operations across multiple providers
    Provides common methods for travel planning tasks
    """

    def __init__(self, provider: AIProvider):
        self.provider = provider

    async def suggest_destinations(
        self, interests: List[str], duration: int, budget: Optional[str] = None, season: Optional[str] = None
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
        return parse_ai_json(response, erwartet=dict, vorgang="Reiseziel-Vorschlaege")

    async def plan_trip(
        self, destination: str, duration: int, interests: List[str], accommodation_type: Optional[str] = None
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

        # Mehr Platz als bei den anderen Anfragen: hier entsteht ein Plan mit
        # Morgen/Mittag/Abend JE TAG plus Tipps. Bei 2048 Token reicht das ab
        # etwa drei Tagen nicht mehr — und seit dem Abbruch-Waechter faellt
        # das als lauter Fehler auf statt als halber Plan.
        response = await self.provider.chat(prompt, max_tokens=4096)
        return parse_ai_json(response, erwartet=dict, vorgang="Reiseplan")

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

    async def chat(self, user_message: str, context: Optional[Dict[str, Any]] = None, max_tokens: int = 2048) -> str:
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

        return await self.provider.chat(user_message, system_prompt=system_prompt, max_tokens=max_tokens)

    async def get_local_tips(self, destination: str, category: str = "all") -> List[Dict[str, str]]:
        """Get local tips and hidden gems"""
        categories_text = {
            "restaurants": "Restaurants und Cafés",
            "sights": "Sehenswürdigkeiten",
            "activities": "Aktivitäten",
            "nightlife": "Nachtleben",
            "all": "alle Kategorien",
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

        # Zehn Tipps mit je sieben Feldern — 2048 Token sind dafuer knapp.
        response = await self.provider.chat(prompt, max_tokens=4096)
        return nur_objekte(parse_ai_json(response, erwartet=list, vorgang="Geheimtipps"), "Geheimtipps")


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
