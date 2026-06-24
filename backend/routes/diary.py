"""
Diary Router
CRUD operations for diary entries
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
from utils.rate_limits import limiter, RateLimits
import asyncio
from utils.images import validate_image, process_and_save
import structlog
from openai import OpenAI

from models.database import get_db
from models.diary import DiaryEntry
from models.trip import Trip
from models.user import User
from models.media import Media
from routes.auth import get_current_active_user, get_optional_user
from routes.media import MediaResponse
from utils.access_control import verify_trip_access
from utils.images import derive_thumb_url, delete_upload_file

logger = structlog.get_logger(__name__)
router = APIRouter()


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Coerce a datetime to tz-naive UTC.

    ``entry_date`` is a ``TIMESTAMP WITHOUT TIME ZONE`` column, so a tz-aware
    value (e.g. an ISO string with an offset, or ``datetime.now(timezone.utc)``)
    makes asyncpg raise ``can't subtract offset-naive and offset-aware``.
    """
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def verify_diary_edit_access(entry, current_user: User, db: AsyncSession) -> None:
    """
    Authorize editing/deleting a diary entry.

    Permitted: the entry's author, the trip owner (for moderation), or a
    superuser. This avoids the owner being locked out of moderating entries
    written by editor-participants, while still keeping editors from altering
    each other's personal entries.
    """
    if current_user.is_superuser or entry.author_id == current_user.id:
        return

    trip_result = await db.execute(select(Trip).where(Trip.id == entry.trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip and trip.owner_id == current_user.id:
        return

    logger.warning(
        "unauthorized_diary_edit",
        entry_id=entry.id,
        user_id=current_user.id,
        author_id=entry.author_id,
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# Upload configuration
UPLOAD_DIR = Path("./uploads/diary")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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
    media: List[MediaResponse] = []
    tags: List[str]
    mood: Optional[str]
    rating: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def photos(self) -> List[str]:
        """Backward-compatible URL list, derived from `media` (the source of truth)."""
        return [m.url for m in self.media]


@router.get("/{trip_id}", response_model=List[DiaryEntryResponse])
@limiter.limit(RateLimits.DIARY_LIST)
async def get_diary_entries(
    request: Request,
    trip_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all diary entries for a trip with pagination. Requires authentication and trip access."""
    # Enforce maximum limit
    limit = min(limit, 500)

    # Verify trip exists and user has access (owner or participant)
    await verify_trip_access(trip_id, current_user, db, require_edit=False)

    # Get diary entries with pagination (media eager-loaded for the response)
    result = await db.execute(
        select(DiaryEntry)
        .options(selectinload(DiaryEntry.media))
        .where(DiaryEntry.trip_id == trip_id)
        .order_by(DiaryEntry.entry_date.desc())
        .offset(skip)
        .limit(limit)
    )
    entries = result.scalars().all()

    logger.info("diary_entries_fetched", trip_id=trip_id, user_id=current_user.id, count=len(entries))

    return entries


async def _load_entry_with_media(entry_id: int, db: AsyncSession) -> DiaryEntry:
    """Re-fetch a diary entry with its media eager-loaded for the response."""
    result = await db.execute(
        select(DiaryEntry)
        .options(selectinload(DiaryEntry.media))
        .where(DiaryEntry.id == entry_id)
    )
    return result.scalar_one()


# Handler function for creating diary entries
async def _create_diary_entry_handler(
    trip_id: int,
    entry: DiaryEntryCreate,
    db: AsyncSession,
    current_user: User
):
    """Create a new diary entry. Requires authentication and edit permission."""
    # Verify trip exists and user has edit access (owner or editor participant)
    await verify_trip_access(trip_id, current_user, db, require_edit=True)

    # Set author
    author_id = current_user.id

    # Create new entry. Photos live in the media table (source of truth), not the
    # legacy `photos` column.
    new_entry = DiaryEntry(
        trip_id=trip_id,
        author_id=author_id,
        title=entry.title,
        content=entry.content,
        entry_date=_to_naive_utc(entry.entry_date) or datetime.now(timezone.utc).replace(tzinfo=None),
        location_name=entry.location_name,
        latitude=entry.latitude,
        longitude=entry.longitude,
        photos=[],
        tags=entry.tags,
        mood=entry.mood,
        rating=entry.rating
    )

    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    # Backward-compat: if a legacy client supplied photo URLs on create, register
    # them as media rows.
    if entry.photos:
        for i, url in enumerate(entry.photos):
            db.add(Media(
                owner_id=author_id,
                trip_id=trip_id,
                diary_entry_id=new_entry.id,
                url=url,
                thumb_url=derive_thumb_url(url),
                order_index=i,
            ))
        await db.commit()

    logger.info("diary_entry_created", entry_id=new_entry.id, trip_id=trip_id, user_id=current_user.id)

    return await _load_entry_with_media(new_entry.id, db)


@router.post("/{trip_id}", response_model=DiaryEntryResponse, status_code=201)
@router.post("/{trip_id}/", response_model=DiaryEntryResponse, status_code=201)
@limiter.limit(RateLimits.DIARY_CREATE)
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
@limiter.limit(RateLimits.DIARY_UPDATE)
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

    # Verify edit rights (author, trip owner, or superuser)
    await verify_diary_edit_access(existing_entry, current_user, db)

    # Update fields. Photos are managed via the media table / media endpoints,
    # so the legacy `photos` column is intentionally left untouched here.
    existing_entry.title = entry.title
    existing_entry.content = entry.content
    existing_entry.entry_date = _to_naive_utc(entry.entry_date) or existing_entry.entry_date
    existing_entry.location_name = entry.location_name
    existing_entry.latitude = entry.latitude
    existing_entry.longitude = entry.longitude
    existing_entry.tags = entry.tags
    existing_entry.mood = entry.mood
    existing_entry.rating = entry.rating
    existing_entry.updated_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info("diary_entry_updated", entry_id=entry_id, user_id=current_user.id)

    return await _load_entry_with_media(entry_id, db)


@router.delete("/{entry_id}", status_code=204)
@limiter.limit(RateLimits.DIARY_DELETE)
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

    # Verify edit rights (author, trip owner, or superuser)
    await verify_diary_edit_access(entry, current_user, db)

    await db.delete(entry)
    await db.commit()

    logger.info("diary_entry_deleted", entry_id=entry_id, user_id=current_user.id)

    return None


@router.get("/{trip_id}/export/markdown")
async def export_diary_markdown(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export diary entries as Markdown. Requires authentication and trip access."""
    # Verify trip exists and user has access
    trip = await verify_trip_access(trip_id, current_user, db, require_edit=False)

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
    current_user: User = Depends(get_current_active_user)
):
    """Export diary entries as PDF. Requires authentication and trip access."""
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

    # Verify trip exists and user has access
    trip = await verify_trip_access(trip_id, current_user, db, require_edit=False)

    # Get diary entries (media eager-loaded for embedding photos)
    result = await db.execute(
        select(DiaryEntry)
        .options(selectinload(DiaryEntry.media))
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
        # Simple markdown to HTML conversion using regex for proper matching
        import re
        content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)  # Bold
        content = re.sub(r'\*(.+?)\*', r'<i>\1</i>', content)      # Italic

        # Split into paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip().replace('\n', '<br/>'), styles['Normal']))
                story.append(Spacer(1, 0.1*inch))

        # Photos (from media, the source of truth)
        photo_urls = [m.url for m in entry.media]
        if photo_urls:
            story.append(Spacer(1, 0.2*inch))

            # Process photos in groups of 2 per row
            photo_rows = []
            for photo_idx in range(0, len(photo_urls), 2):
                row_images = []

                for photo_url in photo_urls[photo_idx:photo_idx + 2]:
                    try:
                        # Convert URL path to file system path SAFELY
                        # photo_url is like "/uploads/diary/uuid.jpg"
                        # Security: Extract only the filename and construct safe path
                        photo_filename = Path(photo_url).name  # Only get filename, no path traversal

                        # Validate filename (must not contain path separators)
                        if '/' in photo_filename or '\\' in photo_filename or '..' in photo_filename:
                            logger.warning("pdf_path_traversal_attempt", photo_url=photo_url)
                            row_images.append(Paragraph(f"<i>Ungültiger Dateipfad</i>", meta_style))
                            continue

                        # Construct safe absolute path
                        photo_file = UPLOAD_DIR / photo_filename

                        if photo_file.exists() and photo_file.is_file():
                            # Create reportlab Image with max width of 2.5 inches
                            img = RLImage(str(photo_file), width=2.5*inch, height=2.5*inch, kind='proportional')
                            row_images.append(img)
                        else:
                            # If file doesn't exist, add placeholder
                            row_images.append(Paragraph(f"<i>Foto nicht gefunden: {photo_filename}</i>", meta_style))
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
@limiter.limit(RateLimits.DIARY_UPLOAD)
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

    # Verify edit rights (author, trip owner, or superuser)
    await verify_diary_edit_access(entry, current_user, db)

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # CRITICAL: Validate file type by content (security check)
    if not validate_image(content, file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only images allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Normalize, compress to WebP, generate a thumbnail and read EXIF metadata.
    try:
        processed = await asyncio.to_thread(process_and_save, content, UPLOAD_DIR, "/uploads/diary")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}")

    # Append after existing media (preserve order).
    count_result = await db.execute(
        select(func.count()).select_from(Media).where(Media.diary_entry_id == entry_id)
    )
    next_index = count_result.scalar() or 0

    new_media = Media(
        owner_id=current_user.id,
        trip_id=entry.trip_id,
        diary_entry_id=entry_id,
        url=processed.url,
        thumb_url=processed.thumb_url,
        mime_type="image/webp",
        width=processed.width,
        height=processed.height,
        size_bytes=processed.size_bytes,
        taken_at=processed.taken_at,
        latitude=processed.latitude,
        longitude=processed.longitude,
        order_index=next_index,
    )
    db.add(new_media)

    # Auto-geotag: if the entry has no coordinates yet, adopt the photo's GPS.
    if entry.latitude is None and processed.latitude is not None:
        entry.latitude = processed.latitude
        entry.longitude = processed.longitude

    entry.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(new_media)

    logger.info(
        "diary_photo_uploaded",
        entry_id=entry_id,
        media_id=new_media.id,
        user_id=current_user.id,
        geotagged=processed.latitude is not None,
    )

    return {
        "message": "Photo uploaded successfully",
        "photo_url": processed.url,
        "thumb_url": processed.thumb_url,
        "media": MediaResponse.model_validate(new_media),
    }


@router.delete("/{entry_id}/photo")
@limiter.limit(RateLimits.DIARY_DELETE)
async def delete_diary_photo(
    request: Request,
    entry_id: int,
    photo_url: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a photo (by URL) from a diary entry. Requires authentication.

    Kept URL-based for backward compatibility; internally it removes the
    corresponding media row (the source of truth) and its files.
    """
    # Get entry
    result = await db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")

    # Verify edit rights (author, trip owner, or superuser)
    await verify_diary_edit_access(entry, current_user, db)

    # Find the media row for this URL
    media_result = await db.execute(
        select(Media).where(Media.diary_entry_id == entry_id, Media.url == photo_url)
    )
    media = media_result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Photo not found in entry")

    thumb_url = media.thumb_url
    await db.delete(media)
    entry.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Remove files (full + thumbnail), contained within the uploads root.
    delete_upload_file(photo_url)
    if thumb_url and thumb_url != photo_url:
        delete_upload_file(thumb_url)

    logger.info("diary_photo_deleted", entry_id=entry_id, user_id=current_user.id)

    return {"message": "Photo deleted successfully"}


class PhotoOrderUpdate(BaseModel):
    media_ids: List[int] = Field(..., description="This entry's media ids in the desired display order")


@router.patch("/{entry_id}/photos/order", response_model=List[MediaResponse])
@limiter.limit(RateLimits.DIARY_UPDATE)
async def reorder_entry_photos(
    request: Request,
    entry_id: int,
    payload: PhotoOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Persist a new display order for a diary entry's photos (drag & drop)."""
    result = await db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    await verify_diary_edit_access(entry, current_user, db)

    media_result = await db.execute(select(Media).where(Media.diary_entry_id == entry_id))
    media_by_id = {m.id: m for m in media_result.scalars().all()}

    # Require an exact permutation of the entry's media, so the order is unambiguous.
    if set(payload.media_ids) != set(media_by_id.keys()):
        raise HTTPException(status_code=400, detail="media_ids must list exactly this entry's photos")

    for index, mid in enumerate(payload.media_ids):
        media_by_id[mid].order_index = index
    entry.updated_at = datetime.now(timezone.utc)
    await db.commit()

    ordered = await db.execute(
        select(Media).where(Media.diary_entry_id == entry_id).order_by(Media.order_index)
    )
    logger.info("diary_photos_reordered", entry_id=entry_id, user_id=current_user.id)
    return ordered.scalars().all()


# ==================== Audio Transcription ====================

@router.post("/transcribe-audio")
@limiter.limit(RateLimits.DIARY_TRANSCRIBE)
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
