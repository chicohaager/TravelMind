"""
Users Router
User profile management
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from models.database import get_db
from models.user import User
from routes.auth import get_current_active_user
from services.audit_service import audit_service
from utils.rate_limits import limiter, RateLimits
from utils.images import validate_image, process_and_save

router = APIRouter()

# Upload configuration
UPLOAD_DIR = Path("./uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class UserProfile(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PublicUserProfile(BaseModel):
    """Public-facing profile exposed to other authenticated users (no email)."""
    id: int
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.get("/profile", response_model=UserProfile)
@limiter.limit(RateLimits.USER_PROFILE_READ)
async def get_profile(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Get current user profile

    Returns detailed profile information of the authenticated user.
    """
    return current_user


@router.put("/profile", response_model=UserProfile)
@limiter.limit(RateLimits.USER_PROFILE_UPDATE)
async def update_profile(
    request: Request,
    profile: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile

    Updates profile information. Only provided fields will be updated.
    """
    # Check if email is being changed and already exists
    if profile.email and profile.email != current_user.email:
        result = await db.execute(select(User).where(User.email == profile.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

    # Update only provided fields
    update_data = profile.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(current_user)

    # Audit log: profile update
    await audit_service.log_data_event(
        db=db,
        action="update",
        resource_type="user_profile",
        resource_id=current_user.id,
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details={"updated_fields": list(update_data.keys())}
    )

    return current_user


@router.post("/change-password")
@limiter.limit(RateLimits.AUTH_PASSWORD_CHANGE)
async def change_password(
    request: Request,
    passwords: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password

    Requires current password for verification.
    """
    # Verify current password
    if not current_user.verify_password(passwords.current_password):
        # Audit log: failed password change attempt
        await audit_service.log_auth_event(
            db=db,
            event="password_change",
            user_id=current_user.id,
            username=current_user.username,
            request=request,
            status="failure",
            details={"reason": "invalid_current_password"}
        )
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    current_user.hashed_password = User.hash_password(passwords.new_password)
    current_user.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Audit log: successful password change
    await audit_service.log_auth_event(
        db=db,
        event="password_change",
        user_id=current_user.id,
        username=current_user.username,
        request=request
    )

    return {"message": "Password changed successfully"}


@router.get("/{user_id}", response_model=PublicUserProfile)
@limiter.limit(RateLimits.USER_PROFILE_READ)
async def get_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the public profile of a user by ID.

    Requires authentication. Returns only public fields (no email).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.delete("/account", status_code=204)
@limiter.limit(RateLimits.USER_DELETE)
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user account

    Permanently deletes the user account and all associated data.
    This action cannot be undone.
    """
    # Store user info for audit log before deletion
    user_id = current_user.id
    username = current_user.username
    email = current_user.email

    # Delete user (cascading will delete all trips, diary entries, etc.)
    await db.delete(current_user)
    await db.commit()

    # Audit log: account deletion (username stored separately since user is deleted)
    await audit_service.log_data_event(
        db=db,
        action="delete",
        resource_type="user_account",
        resource_id=user_id,
        user_id=user_id,
        username=username,
        request=request,
        details={"email": email, "self_deletion": True}
    )

    return None


@router.post("/upload-avatar", response_model=UserProfile)
@limiter.limit(RateLimits.USER_AVATAR_UPLOAD)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload user avatar

    Accepts image files (jpg, jpeg, png, gif, webp) up to 5MB.
    """
    # Read file contents first for validation
    contents = await file.read()

    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024)}MB"
        )

    # Validate file type using MIME detection (not just extension)
    if not validate_image(contents, file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only these image types are allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Normalize, auto-orient and compress. Avatars stay small; no thumbnail needed.
    try:
        processed = process_and_save(
            contents, UPLOAD_DIR, "/uploads/avatars", make_thumb=False, full_max_edge=512
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}")

    # Update user avatar URL
    current_user.avatar_url = processed.url
    current_user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(current_user)

    return current_user
