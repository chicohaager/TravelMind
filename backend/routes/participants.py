"""
Participants Router
Manage trip participants/travelers with photos using SQLite
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import os
import uuid
from pathlib import Path
from models.database import get_db
from models.participant import Participant

router = APIRouter()

# Upload configuration
UPLOAD_DIR = Path("./uploads/participants")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# Request/Response Models
class ParticipantCreate(BaseModel):
    name: str = Field(..., example="Max Mustermann")
    email: Optional[str] = Field(None, example="max@example.com")
    role: Optional[str] = Field(None, example="Freund")


class ParticipantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class ParticipantResponse(BaseModel):
    id: int
    trip_id: int
    name: str
    email: Optional[str]
    role: Optional[str]
    photo_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Helper functions
def validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed"""
    extension = filename.split(".")[-1].lower()
    return extension in ALLOWED_EXTENSIONS


async def save_participant_photo(upload_file: UploadFile, participant_id: int) -> str:
    """Save uploaded participant photo and return the file path"""
    if not validate_file_extension(upload_file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Nur folgende Dateitypen erlaubt: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    contents = await upload_file.read()

    # Check file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximum: {MAX_FILE_SIZE / (1024*1024)}MB"
        )

    # Generate unique filename
    extension = upload_file.filename.split(".")[-1].lower()
    unique_filename = f"participant_{participant_id}_{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Return relative URL path
    return f"/uploads/participants/{unique_filename}"


# Endpoints
@router.get("/{trip_id}/participants", response_model=List[ParticipantResponse])
async def get_participants(trip_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all participants for a trip
    """
    result = await db.execute(
        select(Participant)
        .where(Participant.trip_id == trip_id)
        .order_by(Participant.created_at)
    )
    participants = result.scalars().all()
    return participants


@router.post("/{trip_id}/participants", response_model=ParticipantResponse, status_code=201)
async def create_participant(
    trip_id: int,
    participant: ParticipantCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a participant to a trip
    """
    new_participant = Participant(
        trip_id=trip_id,
        name=participant.name,
        email=participant.email,
        role=participant.role
    )

    db.add(new_participant)
    await db.commit()
    await db.refresh(new_participant)

    return new_participant


@router.put("/participants/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: int,
    participant: ParticipantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update participant information
    """
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    existing_participant = result.scalar_one_or_none()

    if not existing_participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Update only provided fields
    update_data = participant.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_participant, field, value)

    existing_participant.updated_at = datetime.now()

    await db.commit()
    await db.refresh(existing_participant)

    return existing_participant


@router.delete("/participants/{participant_id}", status_code=204)
async def delete_participant(participant_id: int, db: AsyncSession = Depends(get_db)):
    """
    Remove a participant from a trip
    """
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    await db.delete(participant)
    await db.commit()

    return None


@router.post("/participants/{participant_id}/upload-photo", response_model=ParticipantResponse)
async def upload_participant_photo(
    participant_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a photo for a participant

    Accepts image files (jpg, jpeg, png, gif, webp) up to 5MB.
    """
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Save the uploaded file
    file_url = await save_participant_photo(file, participant_id)

    # Update participant with new photo
    participant.photo_url = file_url
    participant.updated_at = datetime.now()

    await db.commit()
    await db.refresh(participant)

    return participant
