"""
AI Assistant Router
Multi-provider AI integration endpoints (Claude, OpenAI, Gemini)
"""

import asyncio
import json
import re
import urllib.parse
from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from models.user import User
from pydantic import BaseModel, Field
from routes.auth import get_current_active_user
from services.ai_service import create_ai_service
from services.pexels_service import get_place_photo
from utils.encryption import encryption_service
from utils.rate_limits import RateLimits, limiter

logger = structlog.get_logger(__name__)

router = APIRouter()


def _parse_ai_json(response: str, erwartet: type = None):
    """Parse a JSON object/array from an AI response.

    Models (Claude, GPT, …) frequently wrap JSON in ```json code fences or add
    a short preamble, so a bare json.loads() fails with "Expecting value: line 1
    column 1". Strip fences, then fall back to extracting the outermost {...} or
    [...]. Raises json.JSONDecodeError if nothing parseable is found.

    `erwartet` nennt die Form, die der Prompt angefordert hat (`list` oder
    `dict`). Sie ist keine Feinheit: der Notfall-Zweig probiert beide Klammer-
    arten, und bei einem ABGESCHNITTENEN Array gibt es kein `]` mehr — dann
    greift die `{…}`-Variante und liefert ein Objekt, das aussieht wie ein
    Ergebnis. Am 2026-08-26 in der Produktion gemessen: der Aufrufer iterierte
    darueber, bekam Schluessel statt Objekte und starb an
    `'str' object has no attribute 'get'` — eine Meldung, die nichts mehr mit
    der Ursache (Token-Limit) zu tun hat. Mit `erwartet=list` wird der falsche
    Zweig gar nicht erst probiert.
    """
    text = (response or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    klammern = {list: (("[", "]"),), dict: (("{", "}"),)}.get(erwartet, (("[", "]"), ("{", "}")))

    try:
        geparst = json.loads(text)
    except json.JSONDecodeError:
        # Try array and object extraction independently so a stray bracket in a
        # preamble can't make us slice across mismatched delimiters.
        geparst = _keine_form = object()
        for open_ch, close_ch in klammern:
            start, end = text.find(open_ch), text.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    geparst = json.loads(text[start : end + 1])
                    break
                except json.JSONDecodeError:
                    continue
        if geparst is _keine_form:
            raise

    if erwartet is not None and not isinstance(geparst, erwartet):
        raise ValueError(
            f"KI-Antwort hat die falsche Form: erwartet {erwartet.__name__}, " f"bekommen {type(geparst).__name__}"
        )
    return geparst


def _nur_objekte(elemente: list, feld: str) -> list:
    """Sicherstellen, dass eine Liste aus Objekten besteht, bevor `.get` darauf laeuft.

    Ohne diesen Schritt entscheidet die KI, ob der Endpunkt mit einem
    AttributeError abstuerzt — und die Meldung nennt dann den Zugriff, nicht
    die Antwort, die ihn verursacht hat.
    """
    falsch = [type(e).__name__ for e in elemente if not isinstance(e, dict)]
    if falsch:
        raise ValueError(
            f"KI-Antwort ({feld}): {len(falsch)} von {len(elemente)} Eintraegen sind keine Objekte ({falsch[:3]})"
        )
    return elemente


def _ki_fehler(vorgang: str, fehler: Exception, user_id: int) -> HTTPException:
    """Einen Anbieterfehler melden, OHNE seine Meldung in die Antwort zu geben.

    Grund, gemessen am 2026-08-25: die Endpunkte haengten `str(e)` an das
    `detail` an. Anbieter-Bibliotheken schreiben den API-Schluessel gern in
    ihre Fehlermeldung ("invalid api key: gsk_…") — der stand damit in der
    HTTP-Antwort, in den Entwicklerwerkzeugen des Browsers, im nginx-Log und
    in jedem Fehlerbericht.

    Die Einzelheiten sind nicht weg, sie gehen nur den anderen Weg: ins
    Protokoll des Servers, wo sie hingehoeren. Die Antwort nennt den Vorgang,
    damit die Meldung fuer den Nutzer noch brauchbar ist.
    """
    logger.error(
        "ai_request_failed",
        vorgang=vorgang,
        user_id=user_id,
        fehler_typ=type(fehler).__name__,
        fehler=str(fehler),
    )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Die KI-Anfrage ({vorgang}) ist fehlgeschlagen. Einzelheiten stehen im Server-Protokoll.",
    )


# Helper function to get user's AI service
def get_user_ai_service(user: User):
    """
    Create an AI service instance for the user

    Raises HTTPException if user hasn't configured their AI settings
    """
    if not user.ai_provider or not user.encrypted_api_key:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "error": "AI_NOT_CONFIGURED",
                "message": "Please configure your AI provider and API key in settings",
                "action": "Go to Settings to configure your AI provider",
            },
        )

    # Decrypt API key using user's unique salt
    if not user.encryption_salt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Encryption salt missing. Please update your API key in settings.",
        )

    api_key = encryption_service.decrypt(user.encrypted_api_key, user.encryption_salt)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key. Please update your API key in settings.",
        )

    # Create AI service
    try:
        return create_ai_service(user.ai_provider.value, api_key)
    except Exception as e:
        logger.error("ai_service_init_failed", user_id=user.id, fehler_typ=type(e).__name__, fehler=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Der KI-Dienst liess sich nicht starten. Bitte den Anbieter in den Einstellungen pruefen.",
        )


# Request/Response Models
class DestinationSuggestionRequest(BaseModel):
    interests: List[str] = Field(..., example=["nature", "culture", "food"])
    duration: int = Field(..., ge=1, le=60, example=7)
    budget: Optional[str] = Field(None, example="medium")
    season: Optional[str] = Field(None, example="summer")


class TripPlanRequest(BaseModel):
    destination: str = Field(..., example="Lissabon")
    duration: int = Field(..., ge=1, le=30, example=5)
    interests: List[str] = Field(..., example=["culture", "food", "photography"])
    accommodation_type: Optional[str] = Field(None, example="boutique hotel")


class DescribeDestinationRequest(BaseModel):
    destination: str = Field(..., example="Kyoto")


class ChatRequest(BaseModel):
    message: str = Field(..., example="Was sind gute Aussichtspunkte in Lissabon?")
    context: Optional[List[Dict[str, str]]] = Field(None)


class LocalTipsRequest(BaseModel):
    destination: str = Field(..., example="Barcelona")
    category: str = Field(default="all", example="restaurants")


class TripFormSuggestionsRequest(BaseModel):
    destination: str = Field(..., example="Barcelona")


class PersonalizedRecommendationsRequest(BaseModel):
    destination: str = Field(..., example="Barcelona")
    interests: List[str] = Field(default=[], example=["culture", "food", "photography"])
    existing_places: List[str] = Field(default=[], example=["Sagrada Familia", "Park Güell"])
    budget: Optional[float] = Field(None, example=1500.0)
    duration: Optional[int] = Field(None, example=5)
    currency: str = Field(default="EUR", example="EUR")


# Endpoints
@router.post("/suggest")
@limiter.limit(RateLimits.AI_RECOMMENDATIONS)
async def suggest_destinations(
    request: Request,
    suggestion_request: DestinationSuggestionRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get destination suggestions based on preferences

    Uses your configured AI provider to recommend destinations that match
    your interests, budget, and other criteria.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        suggestions = await ai_service.suggest_destinations(
            interests=suggestion_request.interests,
            duration=suggestion_request.duration,
            budget=suggestion_request.budget,
            season=suggestion_request.season,
        )
        return suggestions
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.post("/plan")
@limiter.limit(RateLimits.AI_PLAN)
async def plan_trip(
    request: Request, plan_request: TripPlanRequest, current_user: User = Depends(get_current_active_user)
):
    """
    Generate a detailed trip itinerary

    Creates a day-by-day plan with activities, restaurants, costs,
    and practical tips for the specified destination.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        itinerary = await ai_service.plan_trip(
            destination=plan_request.destination,
            duration=plan_request.duration,
            interests=plan_request.interests,
            accommodation_type=plan_request.accommodation_type,
        )
        return itinerary
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.post("/describe")
@limiter.limit(RateLimits.AI_DESCRIBE)
async def describe_destination(
    request: Request,
    describe_request: DescribeDestinationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a poetic, atmospheric description of a destination

    Returns a beautifully written, inspiring description that captures
    the essence, culture, and atmosphere of the destination.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        description = await ai_service.describe_destination(destination=describe_request.destination)
        return {"destination": describe_request.destination, "description": description}
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.post("/chat")
@limiter.limit(RateLimits.AI_CHAT)
async def chat(request: Request, chat_request: ChatRequest, current_user: User = Depends(get_current_active_user)):
    """
    Chat with your AI assistant about travel topics

    Ask any question about destinations, travel tips, planning advice, etc.
    Uses your configured AI provider.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        response = await ai_service.chat(user_message=chat_request.message, context=chat_request.context)
        return {"question": chat_request.message, "answer": response}
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.post("/local-tips")
@limiter.limit(RateLimits.AI_TIPS)
async def get_local_tips(
    request: Request, tips_request: LocalTipsRequest, current_user: User = Depends(get_current_active_user)
):
    """
    Get local tips and hidden gems

    Discover authentic, off-the-beaten-path recommendations
    from a local's perspective.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        tips = await ai_service.get_local_tips(destination=tips_request.destination, category=tips_request.category)
        return {"destination": tips_request.destination, "category": tips_request.category, "tips": tips}
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.post("/trip-suggestions")
@limiter.limit(RateLimits.AI_TIPS)
async def get_trip_suggestions(
    request: Request,
    suggestions_request: TripFormSuggestionsRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get AI-powered suggestions for trip form fields

    Returns suggestions for title, description, interests, budget,
    and recommended duration based on the destination.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        response = await ai_service.chat(
            user_message=f"""Gib mir Vorschläge für eine Reise nach {suggestions_request.destination}.

            Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt in diesem Format:
            {{
                "title": "Kreativer, kurzer Reise-Titel (max 50 Zeichen)",
                "description": "Inspirierende Beschreibung (2-3 Sätze, ca. 150 Zeichen)",
                "interests": ["Interesse1", "Interesse2", "Interesse3", "Interesse4"],
                "budget_min": 800,
                "budget_max": 2000,
                "currency": "EUR",
                "recommended_days": 7
            }}

            Wichtig:
            - Nur JSON zurückgeben, kein zusätzlicher Text
            - Interessen sollten aus dieser Liste sein: Kultur, Natur, Essen, Fotografie, Sport, Geschichte, Strand, Städtereise, Abenteuer, Entspannung
            - Budget in EUR, realistisch für die Destination
            - Deutsche Sprache für alle Texte""",
            context={"destination": suggestions_request.destination},
        )

        # Parse JSON response (tolerates code fences / preamble)
        suggestions = _parse_ai_json(response, erwartet=dict)

        return suggestions
    except ValueError as e:  # deckt JSONDecodeError (Unterklasse) UND die Formpruefung ab
        raise _ki_fehler("Antwort unlesbar", e, current_user.id)
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.post("/personalized-recommendations")
@limiter.limit(RateLimits.AI_RECOMMENDATIONS)
async def get_personalized_recommendations(
    request: Request,
    recommendations_request: PersonalizedRecommendationsRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get personalized place recommendations based on trip details

    Analyzes the user's interests, existing places, and trip details to provide
    smart, personalized recommendations for places to visit that complement their itinerary.
    """
    ai_service = get_user_ai_service(current_user)

    try:
        # Build context about existing places
        places_context = ""
        if recommendations_request.existing_places:
            places_context = f"\n\nBereits geplante Orte: {', '.join(recommendations_request.existing_places)}"

        # Build interests context
        interests_context = ""
        if recommendations_request.interests:
            interests_context = f"\n\nInteressen: {', '.join(recommendations_request.interests)}"

        # Build budget context
        budget_context = ""
        if recommendations_request.budget:
            budget_context = (
                f"\n\nBudget: {recommendations_request.budget} {recommendations_request.currency} (insgesamt)"
            )

        # Build duration context
        duration_context = ""
        if recommendations_request.duration:
            duration_context = f"\n\nReisedauer: {recommendations_request.duration} Tage"

        prompt = f"""Du bist ein Reiseexperte. Analysiere die Reise nach {recommendations_request.destination} und gebe personalisierte Empfehlungen für Orte, die der Reisende noch besuchen sollte.  # noqa: E501
{places_context}{interests_context}{budget_context}{duration_context}

Gib Empfehlungen für Orte, die:
1. Die Interessen des Reisenden treffen
2. Gut zu den bereits geplanten Orten passen (Ergänzung, nicht Duplikate!)
3. Im Rahmen des Budgets und der Reisedauer liegen
4. Eine gute Mischung bieten (Sehenswürdigkeiten, Restaurants, versteckte Juwelen)

Antworte AUSSCHLIESSLICH mit einem validen JSON-Array in diesem Format:
[
  {{
    "name": "Ortsname",
    "category": "attraction|restaurant|beach|viewpoint|museum|park|shopping|nightlife|other",
    "description": "Kurze, ansprechende Beschreibung warum dieser Ort empfohlen wird (1-2 Sätze)",
    "reason": "Warum passt dieser Ort perfekt zu dieser Reise? (1 Satz)",
    "estimated_cost": 15,
    "estimated_duration": "2 Stunden",
    "best_time": "Vormittag|Nachmittag|Abend|Ganztägig",
    "image_search": "Englischer Suchbegriff für Bilder (2-3 Wörter, z.B. 'la palma beach sunset')"
  }}
]

Wichtig:
- Maximal 8 Empfehlungen
- Nur Orte die wirklich zu den Interessen passen
- Deutsche Sprache für name, description, reason
- image_search in ENGLISCH für bessere Bildsuche
- Nur JSON zurückgeben, kein zusätzlicher Text
- Estimated_cost in Zahlen (ohne Währung)
- Verschiedene Kategorien mischen"""

        response = await ai_service.chat(
            user_message=prompt, context={"destination": recommendations_request.destination}
        )

        # Parse JSON response (tolerates code fences / preamble)
        recommendations = _nur_objekte(_parse_ai_json(response, erwartet=list), "recommendations")

        # Enhance each recommendation with image URL and Google Maps link
        # Fetch photos in parallel for better performance
        photo_tasks = [
            get_place_photo(
                place_name=rec.get("image_search", rec["name"]),  # Use AI-generated search term
                category=rec.get("category", "other"),
                destination=recommendations_request.destination,
            )
            for rec in recommendations
        ]
        photo_urls = await asyncio.gather(*photo_tasks)

        for i, rec in enumerate(recommendations):
            # Use Pexels photo URL (or fallback from get_place_photo)
            rec["image_url"] = photo_urls[i]

            # Generate Google Maps search link
            maps_query = f"{rec['name']} {recommendations_request.destination}"
            rec["google_maps_link"] = (
                f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(maps_query)}"
            )

        return {
            "success": True,
            "destination": recommendations_request.destination,
            "recommendations": recommendations,
            "count": len(recommendations),
        }

    except ValueError as e:  # deckt JSONDecodeError (Unterklasse) UND die Formpruefung ab
        raise _ki_fehler("Antwort unlesbar", e, current_user.id)
    except Exception as e:
        raise _ki_fehler("Anfrage", e, current_user.id)


@router.get("/status")
@limiter.limit(RateLimits.AI_CHAT)
async def ai_status(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Check if AI features are configured for the current user
    """
    try:
        is_configured = current_user.ai_provider is not None and current_user.encrypted_api_key is not None

        return {
            "configured": is_configured,
            "provider": current_user.ai_provider.value if current_user.ai_provider else None,
            "message": (
                "AI is configured and ready" if is_configured else "Please configure your AI provider in settings"
            ),
        }
    except Exception:
        return {"configured": False, "provider": None, "message": "AI configuration not available"}
