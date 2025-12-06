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
import uuid
import magic

from models.database import get_db
from models.user import User
from routes.auth import get_current_active_user
from services.audit_service import audit_service
from utils.rate_limits import limiter, RateLimits

router = APIRouter()

# Upload configuration
UPLOAD_DIR = Path("./uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_file(contents: bytes, filename: str) -> bool:
    """
    Validate image file by checking actual content, not just extension.
    Uses python-magic to detect MIME type from file content.
    """
    extension = filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False

    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(contents)

    return mime_type in ALLOWED_MIME_TYPES


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


@router.get("/{user_id}", response_model=UserProfile)
@limiter.limit(RateLimits.USER_PROFILE_READ)
async def get_user(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get user profile by ID

    Returns public profile information of any user.
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
    if not validate_image_file(contents, file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only these image types are allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    extension = file.filename.split(".")[-1].lower()
    unique_filename = f"user_{current_user.id}_{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Update user avatar URL
    current_user.avatar_url = f"/uploads/avatars/{unique_filename}"
    current_user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(current_user)

    return current_user
