"""
Diary Router
CRUD operations for diary entries
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO
import os
import uuid
import magic
from pathlib import Path
from slowapi import Limiter
from slowapi.util import get_remote_address
import structlog
from openai import OpenAI

from models.database import get_db
from models.diary import DiaryEntry
from models.trip import Trip
from models.user import User
from routes.auth import get_current_active_user, get_optional_user

logger = structlog.get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Upload configuration
UPLOAD_DIR = Path("./uploads/diary")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_photo_type(contents: bytes, filename: str) -> bool:
    """
    Validate photo file type by checking actual content, not just extension.
    Uses python-magic to detect MIME type from file content.
    """
    extension = filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False

    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(contents)

    return mime_type in ALLOWED_MIME_TYPES


class DiaryEntryCreate(BaseModel):
    title: str = Field(..., example="Tag 1 in Lissabon")
    content: str = Field(..., example="# Heute...\n\nEin wundervoller Tag!")
    entry_date: Optional[datetime] = None
    location_name: Optional[str] = Field(None, example="Alfama")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photos: List[str] = Field(default=[], example=["photo1.jpg"])
    tags: List[str] = Field(default=[], example=["food", "sunset"])
    mood: Optional[str] = Field(None, example="happy")
    rating: Optional[int] = Field(None, ge=1, le=5, example=5)


class DiaryEntryResponse(BaseModel):
    id: int
    title: str
    content: str
    entry_date: Optional[datetime]
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    photos: List[str]
    tags: List[str]
    mood: Optional[str]
    rating: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/{trip_id}", response_model=List[DiaryEntryResponse])
@limiter.limit("60/minute")
async def get_diary_entries(
    request: Request,
    trip_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all diary entries for a trip with pagination. Requires authentication and trip ownership."""
    # Enforce maximum limit
    limit = min(limit, 500)

    # Verify trip exists and user has access
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if trip.owner_id != current_user.id:
        logger.warning("unauthorized_diary_access", trip_id=trip_id, user_id=current_user.id, owner_id=trip.owner_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get diary entries with pagination
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.trip_id == trip_id)
        .order_by(DiaryEntry.entry_date.desc())
        .offset(skip)
        .limit(limit)
    )
    entries = result.scalars().all()

    logger.info("diary_entries_fetched", trip_id=trip_id, user_id=current_user.id, count=len(entries))

    return entries


# Handler function for creating diary entries
async def _create_diary_entry_handler(
    trip_id: int,
    entry: DiaryEntryCreate,
    db: AsyncSession,
    current_user: User
):
    """Create a new diary entry. Requires authentication and trip ownership."""
    # Verify trip exists
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if trip.owner_id != current_user.id:
        logger.warning("unauthorized_diary_create", trip_id=trip_id, user_id=current_user.id, owner_id=trip.owner_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Set author
    author_id = current_user.id

    # Create new entry
    new_entry = DiaryEntry(
        trip_id=trip_id,
        author_id=author_id,
        title=entry.title,
        content=entry.content,
        entry_date=entry.entry_date or datetime.now(timezone.utc),
        location_name=entry.location_name,
        latitude=entry.latitude,
        longitude=entry.longitude,
        photos=entry.photos,
        tags=entry.tags,
        mood=entry.mood,
        rating=entry.rating
    )

    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    logger.info("diary_entry_created", entry_id=new_entry.id, trip_id=trip_id, user_id=current_user.id)

    return new_entry


@router.post("/{trip_id}", response_model=DiaryEntryResponse, status_code=201)
@router.post("/{trip_id}/", response_model=DiaryEntryResponse, status_code=201)
@limiter.limit("20/minute")
async def create_diary_entry(
    request: Request,
    trip_id: int,
    entry: DiaryEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new diary entry. Requires authentication and trip ownership."""
    return await _create_diary_entry_handler(trip_id, entry, db, current_user)


@router.put("/{entry_id}", response_model=DiaryEntryResponse)
@limiter.limit("30/minute")
async def update_diary_entry(
    request: Request,
    entry_id: int,
    entry: DiaryEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a diary entry. Requires authentication and ownership."""
    # Get existing entry
    result = await db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
    existing_entry = result.scalar_one_or_none()

    if not existing_entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")

    # Verify ownership
    if existing_entry.author_id != current_user.id:
        logger.warning("unauthorized_diary_update", entry_id=entry_id, user_id=current_user.id, author_id=existing_entry.author_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Update fields
    existing_entry.title = entry.title
    existing_entry.content = entry.content
    existing_entry.entry_date = entry.entry_date or existing_entry.entry_date
    existing_entry.location_name = entry.location_name
    existing_entry.latitude = entry.latitude
    existing_entry.longitude = entry.longitude
    existing_entry.photos = entry.photos
    existing_entry.tags = entry.tags
    existing_entry.mood = entry.mood
    existing_entry.rating = entry.rating
    existing_entry.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(existing_entry)

    logger.info("diary_entry_updated", entry_id=entry_id, user_id=current_user.id)

    return existing_entry


@router.delete("/{entry_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_diary_entry(
    request: Request,
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a diary entry. Requires authentication and ownership."""
    # Get existing entry
    result = await db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")

    # Verify ownership
    if entry.author_id != current_user.id:
        logger.warning("unauthorized_diary_delete", entry_id=entry_id, user_id=current_user.id, author_id=entry.author_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await db.delete(entry)
    await db.commit()

    logger.info("diary_entry_deleted", entry_id=entry_id, user_id=current_user.id)

    return None


@router.get("/{trip_id}/export/markdown")
async def export_diary_markdown(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Export diary entries as Markdown"""
    # Get trip info
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if current_user and trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get diary entries
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.trip_id == trip_id)
        .order_by(DiaryEntry.entry_date.asc())
    )
    entries = result.scalars().all()

    if not entries:
        raise HTTPException(status_code=404, detail="No diary entries found")

    # Build markdown content
    markdown_lines = []
    markdown_lines.append(f"# {trip.title}")
    markdown_lines.append(f"\n**Reiseziel:** {trip.destination}")

    if trip.start_date and trip.end_date:
        markdown_lines.append(f"**Zeitraum:** {trip.start_date.strftime('%d.%m.%Y')} bis {trip.end_date.strftime('%d.%m.%Y')}")

    markdown_lines.append("\n---\n")

    for entry in entries:
        # Entry header
        markdown_lines.append(f"## {entry.title}")

        # Date
        if entry.entry_date:
            date_str = entry.entry_date.strftime("%d.%m.%Y")
            markdown_lines.append(f"\n**Datum:** {date_str}")

        # Location
        if entry.location_name:
            markdown_lines.append(f"**Ort:** {entry.location_name}")

        # Rating
        if entry.rating:
            stars = '⭐' * entry.rating
            markdown_lines.append(f"**Bewertung:** {stars}")

        # Mood
        if entry.mood:
            mood_icons = {'happy': '😊', 'neutral': '😐', 'sad': '☹️'}
            mood_icon = mood_icons.get(entry.mood, '')
            markdown_lines.append(f"**Stimmung:** {mood_icon}")

        # Tags
        if entry.tags and len(entry.tags) > 0:
            tags_str = ', '.join(f"`{tag}`" for tag in entry.tags)
            markdown_lines.append(f"**Tags:** {tags_str}")

        markdown_lines.append("")  # Empty line before content

        # Content
        markdown_lines.append(entry.content)

        markdown_lines.append("\n---\n")

    markdown_content = '\n'.join(markdown_lines)

    # Return as downloadable file
    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=\"{trip.title.replace(' ', '_')}.md\""
        }
    )


@router.get("/{trip_id}/export/pdf")
async def export_diary_pdf(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Export diary entries as PDF"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage, Table
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF export requires reportlab library. Install with: pip install reportlab"
        )

    # Get trip info
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if current_user and trip.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get diary entries
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.trip_id == trip_id)
        .order_by(DiaryEntry.entry_date.asc())
    )
    entries = result.scalars().all()

    if not entries:
        raise HTTPException(status_code=404, detail="No diary entries found")

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch)

    # Container for PDF elements
    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#2563eb',
        spaceAfter=12,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor='#1e40af',
        spaceAfter=6,
        spaceBefore=12
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#6b7280'
    )

    # Title page
    story.append(Paragraph(trip.title, title_style))
    story.append(Spacer(1, 0.2*inch))

    if trip.destination:
        story.append(Paragraph(f"<b>Reiseziel:</b> {trip.destination}", meta_style))

    if trip.start_date and trip.end_date:
        story.append(Paragraph(f"<b>Zeitraum:</b> {trip.start_date.strftime('%d.%m.%Y')} bis {trip.end_date.strftime('%d.%m.%Y')}", meta_style))

    story.append(Spacer(1, 0.5*inch))
    story.append(PageBreak())

    # Entries
    for i, entry in enumerate(entries):
        # Entry title
        story.append(Paragraph(entry.title, heading_style))

        # Meta information
        meta_parts = []

        if entry.entry_date:
            date_str = entry.entry_date.strftime("%d.%m.%Y")
            meta_parts.append(f"<b>Datum:</b> {date_str}")

        if entry.location_name:
            meta_parts.append(f"<b>Ort:</b> {entry.location_name}")

        if entry.rating:
            stars = '★' * entry.rating + '☆' * (5 - entry.rating)
            meta_parts.append(f"<b>Bewertung:</b> {stars}")

        if entry.mood:
            mood_labels = {'happy': 'Glücklich', 'neutral': 'Neutral', 'sad': 'Traurig'}
            mood_label = mood_labels.get(entry.mood, entry.mood)
            meta_parts.append(f"<b>Stimmung:</b> {mood_label}")

        if meta_parts:
            story.append(Paragraph(' | '.join(meta_parts), meta_style))
            story.append(Spacer(1, 0.1*inch))

        # Tags
        if entry.tags and len(entry.tags) > 0:
            tags_str = ', '.join(entry.tags)
            story.append(Paragraph(f"<b>Tags:</b> {tags_str}", meta_style))
            story.append(Spacer(1, 0.1*inch))

        # Content - convert markdown-style formatting to basic HTML
        content = entry.content
        # Simple markdown to HTML conversion
        content = content.replace('**', '<b>').replace('**', '</b>')
        content = content.replace('*', '<i>').replace('*', '</i>')

        # Split into paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip().replace('\n', '<br/>'), styles['Normal']))
                story.append(Spacer(1, 0.1*inch))

        # Photos
        if entry.photos and len(entry.photos) > 0:
            story.append(Spacer(1, 0.2*inch))

            # Process photos in groups of 2 per row
            photo_rows = []
            for photo_idx in range(0, len(entry.photos), 2):
                row_images = []

                for photo_url in entry.photos[photo_idx:photo_idx + 2]:
                    try:
                        # Convert URL path to file system path
                        # photo_url is like "/uploads/diary/uuid.jpg"
                        photo_path = photo_url.lstrip('/')  # Remove leading slash
                        photo_file = Path(photo_path)

                        if photo_file.exists():
                            # Create reportlab Image with max width of 2.5 inches
                            img = RLImage(str(photo_file), width=2.5*inch, height=2.5*inch, kind='proportional')
                            row_images.append(img)
                        else:
                            # If file doesn't exist, add placeholder
                            row_images.append(Paragraph(f"<i>Foto nicht gefunden: {photo_file.name}</i>", meta_style))
                    except Exception as e:
                        # If image loading fails, add error message
                        logger.warning("pdf_image_error", photo_url=photo_url, error=str(e))
                        row_images.append(Paragraph(f"<i>Fehler beim Laden</i>", meta_style))

                if row_images:
                    photo_rows.append(row_images)

            # Add photos as table for layout
            if photo_rows:
                photo_table = Table(photo_rows, colWidths=[2.7*inch, 2.7*inch])
                photo_table.setStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ])
                story.append(photo_table)
                story.append(Spacer(1, 0.2*inch))

        # Add space between entries (but not after last entry)
        if i < len(entries) - 1:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph('─' * 80, meta_style))
            story.append(Spacer(1, 0.2*inch))

    # Build PDF
    doc.build(story)

    # Get PDF content
    pdf_content = buffer.getvalue()
    buffer.close()

    # Return as downloadable file
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{trip.title.replace(' ', '_')}.pdf\""
        }
    )


@router.post("/{entry_id}/upload-photo")
@limiter.limit("10/minute")
async def upload_diary_photo(
    request: Request,
    entry_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a photo to a diary entry.
    Requires authentication and ownership. Validates file content for security.
    """
    # Get entry
    result = await db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")

    # Verify ownership
    if entry.author_id != current_user.id:
        logger.warning("unauthorized_diary_access", entry_id=entry_id, user_id=current_user.id, author_id=entry.author_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # CRITICAL: Validate file type by content (security check)
    if not validate_photo_type(content, file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only images allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    file_ext = file.filename.split('.')[-1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Add photo to entry
    photo_url = f"/uploads/diary/{unique_filename}"
    if entry.photos is None:
        entry.photos = []
    entry.photos = entry.photos + [photo_url]  # Create new list for SQLAlchemy change tracking
    entry.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(entry)

    logger.info("diary_photo_uploaded", entry_id=entry_id, filename=unique_filename, user_id=current_user.id)

    return {
        "message": "Photo uploaded successfully",
        "photo_url": photo_url,
        "entry": entry
    }


@router.delete("/{entry_id}/photo")
async def delete_diary_photo(
    entry_id: int,
    photo_url: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Delete a photo from a diary entry"""
    # Get entry
    result = await db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")

    # Verify ownership
    if current_user and entry.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if photo exists in entry
    if not entry.photos or photo_url not in entry.photos:
        raise HTTPException(status_code=404, detail="Photo not found in entry")

    # Remove from entry
    new_photos = [p for p in entry.photos if p != photo_url]
    entry.photos = new_photos
    entry.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(entry)

    # Delete file if exists
    try:
        filename = photo_url.split('/')[-1]
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            os.remove(file_path)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error deleting file: {e}")

    return {
        "message": "Photo deleted successfully",
        "entry": entry
    }

# ==================== Audio Transcription ====================

@router.post("/transcribe-audio")
@limiter.limit("20/minute")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transcribe audio to text using OpenAI Whisper API.
    
    Accepts audio files in formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Max file size: 25MB
    """
    try:
        # Validate file type
        allowed_types = ['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/wav', 'audio/webm', 'audio/ogg']
        allowed_extensions = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.ogg']
        
        file_ext = os.path.splitext(audio.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read audio file
        audio_content = await audio.read()
        
        # Validate size (max 25MB for Whisper API)
        max_size = 25 * 1024 * 1024  # 25MB
        if len(audio_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="Audio file too large. Maximum size is 25MB"
            )
        
        # Get OpenAI API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please add OPENAI_API_KEY to your environment."
            )
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create a temporary file-like object
        audio_file = BytesIO(audio_content)
        audio_file.name = audio.filename
        
        # Transcribe using Whisper API
        logger.info("transcribing_audio", user_id=current_user.id, filename=audio.filename, size=len(audio_content))
        
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="de",  # Deutsch - kann auch auto-detect mit None
            response_format="text"
        )
        
        logger.info("transcription_complete", user_id=current_user.id, text_length=len(transcript))
        
        return {
            "success": True,
            "text": transcript,
            "filename": audio.filename,
            "size": len(audio_content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("transcription_failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
