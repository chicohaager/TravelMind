"""
Users Router
User profile management
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from pathlib import Path
import uuid

from models.database import get_db
from models.user import User
from routes.auth import get_current_active_user

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


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get current user profile

    Returns detailed profile information of the authenticated user.
    """
    return current_user


@router.put("/profile", response_model=UserProfile)
async def update_profile(
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

    current_user.updated_at = datetime.now()

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/change-password")
async def change_password(
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
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    current_user.hashed_password = User.hash_password(passwords.new_password)
    current_user.updated_at = datetime.now()

    await db.commit()

    return {"message": "Password changed successfully"}


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
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
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user account

    Permanently deletes the user account and all associated data.
    This action cannot be undone.
    """
    # Delete user (cascading will delete all trips, diary entries, etc.)
    await db.delete(current_user)
    await db.commit()

    return None


@router.post("/upload-avatar", response_model=UserProfile)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload user avatar

    Accepts image files (jpg, jpeg, png, gif, webp) up to 5MB.
    """
    # Validate file extension
    extension = file.filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only these file types are allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024)}MB"
        )

    # Generate unique filename
    unique_filename = f"user_{current_user.id}_{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Update user avatar URL
    current_user.avatar_url = f"/uploads/avatars/{unique_filename}"
    current_user.updated_at = datetime.now()

    await db.commit()
    await db.refresh(current_user)

    return current_user
