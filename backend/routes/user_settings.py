"""
User Settings Router
Manage user preferences including AI provider configuration
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from models.database import get_db
from models.user import AIProvider, User
from pydantic import BaseModel, Field
from routes.auth import get_current_active_user
from sqlalchemy.ext.asyncio import AsyncSession
from utils.encryption import encryption_service
from utils.rate_limits import RateLimits, limiter

logger = structlog.get_logger(__name__)

router = APIRouter()


# Pydantic Models
class AISettingsResponse(BaseModel):
    """Response model for AI settings (never returns API key)"""

    ai_provider: Optional[str] = None
    has_api_key: bool = False

    class Config:
        from_attributes = True


class AISettingsUpdate(BaseModel):
    """Request model for updating AI settings"""

    ai_provider: str = Field(..., description="AI provider: groq (FREE), claude, openai, or gemini")
    api_key: str = Field(..., min_length=10, description="API key for the selected provider")


class UserSettingsResponse(BaseModel):
    """Complete user settings response"""

    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    ai_settings: AISettingsResponse

    class Config:
        from_attributes = True


# Endpoints
@router.get("/settings", response_model=UserSettingsResponse)
@limiter.limit(RateLimits.USER_PROFILE_READ)
async def get_user_settings(
    request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Get current user settings including AI configuration

    Returns user profile and AI settings (API key is never returned for security)
    """
    ai_settings = AISettingsResponse(
        ai_provider=current_user.ai_provider.value if current_user.ai_provider else None,
        has_api_key=bool(current_user.encrypted_api_key),
    )

    return UserSettingsResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        ai_settings=ai_settings,
    )


@router.get("/settings/ai", response_model=AISettingsResponse)
@limiter.limit(RateLimits.USER_PROFILE_READ)
async def get_ai_settings(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Get AI provider settings

    Returns which AI provider is configured and whether an API key is set.
    The actual API key is never returned for security reasons.
    """
    return AISettingsResponse(
        ai_provider=current_user.ai_provider.value if current_user.ai_provider else None,
        has_api_key=bool(current_user.encrypted_api_key),
    )


@router.put("/settings/ai", response_model=AISettingsResponse)
@limiter.limit("20/minute")
async def update_ai_settings(
    request: Request,
    settings: AISettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update AI provider and API key

    Sets the AI provider (groq, claude, openai, or gemini) and encrypts the API key
    for secure storage.
    """
    # Validate provider
    provider_lower = settings.ai_provider.lower()
    if provider_lower not in ["groq", "claude", "openai", "gemini"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI provider. Must be one of: groq, claude, openai, gemini",
        )

    # Map string to enum
    provider_map = {
        "groq": AIProvider.GROQ,
        "claude": AIProvider.CLAUDE,
        "openai": AIProvider.OPENAI,
        "gemini": AIProvider.GEMINI,
    }

    # Generate a new salt for this user if they don't have one
    if not current_user.encryption_salt:
        current_user.encryption_salt = encryption_service.generate_salt()

    # Encrypt API key with user's unique salt
    encrypted_key = encryption_service.encrypt(settings.api_key, current_user.encryption_salt)

    # Update user
    current_user.ai_provider = provider_map[provider_lower]
    current_user.encrypted_api_key = encrypted_key

    await db.commit()
    await db.refresh(current_user)

    return AISettingsResponse(ai_provider=current_user.ai_provider.value, has_api_key=True)


@router.delete("/settings/ai")
@limiter.limit("20/minute")
async def delete_ai_settings(
    request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    Delete AI provider settings

    Removes the stored API key and resets the AI provider configuration.
    Note: Salt is kept for potential future use.
    """
    current_user.ai_provider = None
    current_user.encrypted_api_key = None
    # Keep the salt for future use, no need to delete it

    await db.commit()

    return {"message": "AI settings deleted successfully", "ai_provider": None, "has_api_key": False}


@router.post("/settings/ai/validate")
@limiter.limit("10/minute")
async def validate_api_key(
    request: Request, settings: AISettingsUpdate, current_user: User = Depends(get_current_active_user)
):
    """
    Validate an API key without saving it

    Tests if the provided API key works with the selected provider
    by making a simple API call.
    """
    provider_lower = settings.ai_provider.lower()
    if provider_lower not in ["groq", "claude", "openai", "gemini"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI provider. Must be one of: groq, claude, openai, gemini",
        )

    try:
        # Import here to avoid circular dependencies
        from services.ai_service import create_ai_service

        # Create a temporary AI service
        ai_service = create_ai_service(provider_lower, settings.api_key)

        # Make a simple test call
        await ai_service.provider.chat(prompt="Say 'API key valid' in one word", max_tokens=10)

        return {"valid": True, "provider": provider_lower, "message": "API key is valid and working"}

    except Exception as e:
        # NICHT `str(e)` in die Antwort: Anbieter-Bibliotheken schreiben den
        # geprueften Schluessel gern in ihre Fehlermeldung ("invalid api key:
        # gsk_…"). Er stuende dann in der HTTP-Antwort, in den
        # Entwicklerwerkzeugen des Browsers und im Proxy-Protokoll — genau der
        # Wert, den dieser Endpunkt schuetzen soll. Dieselbe Ursache wie in
        # routes/ai.py, am 2026-08-25 an beiden Stellen behoben.
        logger.warning(
            "ai_key_validation_failed",
            provider=provider_lower,
            user_id=current_user.id,
            fehler_typ=type(e).__name__,
            fehler=str(e),
        )
        return {
            "valid": False,
            "provider": provider_lower,
            "message": f"Der Schluessel wurde vom Anbieter abgelehnt ({type(e).__name__}).",
        }
