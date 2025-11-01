"""
User Settings Router
Manage user preferences including AI provider configuration
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from models.database import get_db
from models.user import User, AIProvider
from routes.auth import get_current_active_user
from utils.encryption import encryption_service

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
async def get_user_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user settings including AI configuration

    Returns user profile and AI settings (API key is never returned for security)
    """
    ai_settings = AISettingsResponse(
        ai_provider=current_user.ai_provider.value if current_user.ai_provider else None,
        has_api_key=bool(current_user.encrypted_api_key)
    )

    return UserSettingsResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        ai_settings=ai_settings
    )


@router.get("/settings/ai", response_model=AISettingsResponse)
async def get_ai_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AI provider settings

    Returns which AI provider is configured and whether an API key is set.
    The actual API key is never returned for security reasons.
    """
    return AISettingsResponse(
        ai_provider=current_user.ai_provider.value if current_user.ai_provider else None,
        has_api_key=bool(current_user.encrypted_api_key)
    )


@router.put("/settings/ai", response_model=AISettingsResponse)
async def update_ai_settings(
    settings: AISettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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
            detail="Invalid AI provider. Must be one of: groq, claude, openai, gemini"
        )

    # Map string to enum
    provider_map = {
        "groq": AIProvider.GROQ,
        "claude": AIProvider.CLAUDE,
        "openai": AIProvider.OPENAI,
        "gemini": AIProvider.GEMINI
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

    return AISettingsResponse(
        ai_provider=current_user.ai_provider.value,
        has_api_key=True
    )


@router.delete("/settings/ai")
async def delete_ai_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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

    return {
        "message": "AI settings deleted successfully",
        "ai_provider": None,
        "has_api_key": False
    }


@router.post("/settings/ai/validate")
async def validate_api_key(
    settings: AISettingsUpdate,
    current_user: User = Depends(get_current_active_user)
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
            detail="Invalid AI provider. Must be one of: groq, claude, openai, gemini"
        )

    try:
        # Import here to avoid circular dependencies
        from services.ai_service import create_ai_service

        # Create a temporary AI service
        ai_service = create_ai_service(provider_lower, settings.api_key)

        # Make a simple test call
        test_response = await ai_service.provider.chat(
            prompt="Say 'API key valid' in one word",
            max_tokens=10
        )

        return {
            "valid": True,
            "provider": provider_lower,
            "message": "API key is valid and working"
        }

    except Exception as e:
        return {
            "valid": False,
            "provider": provider_lower,
            "message": f"API key validation failed: {str(e)}"
        }
