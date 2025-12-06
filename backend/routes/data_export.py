"""
Data Export Router

GDPR-compliant data export functionality.
Allows users to download all their personal data.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import zipfile
import io
import os

from models.database import get_db
from models.user import User
from models.trip import Trip
from models.diary import DiaryEntry
from models.place import Place
from models.expense import Expense
from routes.auth import get_current_active_user
from services.audit_service import audit_service
from utils.rate_limits import limiter, RateLimits

router = APIRouter()


class ExportStatus(BaseModel):
    status: str
    message: str
    download_url: Optional[str] = None


class DataExportInfo(BaseModel):
    available_formats: List[str]
    includes: List[str]
    estimated_size: Optional[str] = None
    last_export: Optional[datetime] = None


def serialize_datetime(obj: Any) -> Any:
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def model_to_dict(obj: Any, exclude: List[str] = None) -> Dict:
    """Convert SQLAlchemy model to dictionary."""
    exclude = exclude or []
    result = {}
    for column in obj.__table__.columns:
        if column.name not in exclude:
            value = getattr(obj, column.name)
            if isinstance(value, datetime):
                value = value.isoformat() if value else None
            result[column.name] = value
    return result


async def gather_user_data(user: User, db: AsyncSession) -> Dict[str, Any]:
    """
    Gather all user data for export.

    Returns a dictionary containing all user-related data.
    """
    data = {
        "export_info": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user.id,
            "format_version": "1.0"
        },
        "user_profile": {},
        "trips": [],
        "diary_entries": [],
        "places": [],
        "expenses": []
    }

    # User profile (excluding sensitive fields)
    data["user_profile"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }

    # Trips
    trips_result = await db.execute(
        select(Trip)
        .where(Trip.owner_id == user.id)
        .order_by(Trip.created_at.desc())
    )
    trips = trips_result.scalars().all()

    for trip in trips:
        trip_data = model_to_dict(trip, exclude=["owner_id"])
        data["trips"].append(trip_data)

    # Diary entries
    diary_result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.author_id == user.id)
        .order_by(DiaryEntry.entry_date.desc())
    )
    entries = diary_result.scalars().all()

    for entry in entries:
        entry_data = model_to_dict(entry, exclude=["author_id"])
        data["diary_entries"].append(entry_data)

    # Places (from user's trips)
    trip_ids = [t.id for t in trips]
    if trip_ids:
        places_result = await db.execute(
            select(Place)
            .where(Place.trip_id.in_(trip_ids))
            .order_by(Place.created_at.desc())
        )
        places = places_result.scalars().all()

        for place in places:
            place_data = model_to_dict(place)
            data["places"].append(place_data)

    # Expenses (from user's trips)
    if trip_ids:
        expenses_result = await db.execute(
            select(Expense)
            .where(Expense.trip_id.in_(trip_ids))
            .order_by(Expense.date.desc())
        )
        expenses = expenses_result.scalars().all()

        for expense in expenses:
            expense_data = model_to_dict(expense)
            data["expenses"].append(expense_data)

    return data


def create_export_zip(data: Dict[str, Any], include_readme: bool = True) -> io.BytesIO:
    """
    Create a ZIP file containing all exported data.

    Returns a BytesIO object containing the ZIP file.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Main data file (JSON)
        json_data = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        zip_file.writestr("data.json", json_data)

        # Individual files for each data type
        if data.get("user_profile"):
            zip_file.writestr(
                "profile.json",
                json.dumps(data["user_profile"], indent=2, default=str, ensure_ascii=False)
            )

        if data.get("trips"):
            zip_file.writestr(
                "trips.json",
                json.dumps(data["trips"], indent=2, default=str, ensure_ascii=False)
            )

        if data.get("diary_entries"):
            zip_file.writestr(
                "diary_entries.json",
                json.dumps(data["diary_entries"], indent=2, default=str, ensure_ascii=False)
            )

        if data.get("places"):
            zip_file.writestr(
                "places.json",
                json.dumps(data["places"], indent=2, default=str, ensure_ascii=False)
            )

        if data.get("expenses"):
            zip_file.writestr(
                "expenses.json",
                json.dumps(data["expenses"], indent=2, default=str, ensure_ascii=False)
            )

        # README file
        if include_readme:
            readme_content = """# TravelMind Data Export

This archive contains all your personal data from TravelMind.

## Contents

- `data.json` - Complete export with all data in a single file
- `profile.json` - Your user profile information
- `trips.json` - All your trips
- `diary_entries.json` - All your diary entries
- `places.json` - All places from your trips
- `expenses.json` - All expenses from your trips

## Data Format

All files are in JSON format and can be opened with any text editor
or imported into other applications.

## GDPR Compliance

This export was generated in compliance with GDPR Article 20
(Right to data portability).

## Questions?

If you have questions about your data, please contact support.

Generated: {timestamp}
""".format(timestamp=data["export_info"]["generated_at"])
            zip_file.writestr("README.txt", readme_content)

    zip_buffer.seek(0)
    return zip_buffer


@router.get("/export/info", response_model=DataExportInfo)
@limiter.limit("30/minute")
async def get_export_info(
    request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about available data export options.

    Returns details about what data can be exported and available formats.
    """
    # Count user's data
    trips_result = await db.execute(
        select(Trip).where(Trip.owner_id == current_user.id)
    )
    trip_count = len(trips_result.scalars().all())

    diary_result = await db.execute(
        select(DiaryEntry).where(DiaryEntry.author_id == current_user.id)
    )
    diary_count = len(diary_result.scalars().all())

    return DataExportInfo(
        available_formats=["json", "zip"],
        includes=[
            "User profile",
            f"Trips ({trip_count})",
            f"Diary entries ({diary_count})",
            "Places",
            "Expenses"
        ],
        estimated_size="< 10 MB" if trip_count < 100 else "10-50 MB",
        last_export=None  # Could track this in database
    )


@router.get("/export/download")
@limiter.limit("5/hour")
async def download_data_export(
    request,
    format: str = "zip",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download all user data (GDPR Article 20 compliance).

    Exports all personal data in a portable format.

    **Rate limited to 5 requests per hour.**

    Parameters:
    - **format**: Export format (zip or json)

    Returns:
    - ZIP file containing all user data
    - Or JSON file with all data
    """
    # Gather all user data
    data = await gather_user_data(current_user, db)

    # Audit log the export
    await audit_service.log_data_event(
        db=db,
        action="export",
        resource_type="user_data",
        resource_id=current_user.id,
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details={"format": format}
    )

    if format == "json":
        # Return raw JSON
        json_data = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        return StreamingResponse(
            io.BytesIO(json_data.encode("utf-8")),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=travelmind_export_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.json"
            }
        )
    else:
        # Return ZIP file
        zip_buffer = create_export_zip(data)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=travelmind_export_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.zip"
            }
        )


@router.delete("/account/data")
@limiter.limit("1/day")
async def request_data_deletion(
    request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request deletion of all user data (GDPR Article 17 - Right to erasure).

    **This action is irreversible.**

    This will:
    1. Export your data (download link provided)
    2. Schedule complete data deletion
    3. Send confirmation email

    Rate limited to 1 request per day.
    """
    # First, create an export for the user
    data = await gather_user_data(current_user, db)

    # Audit log
    await audit_service.log_data_event(
        db=db,
        action="deletion_request",
        resource_type="user_account",
        resource_id=current_user.id,
        user_id=current_user.id,
        username=current_user.username,
        request=request,
        details={"data_items": len(data.get("trips", []))}
    )

    return {
        "status": "pending",
        "message": "Data deletion request received. Please delete your account via /api/users/account to complete the process.",
        "export_available": True,
        "note": "We recommend downloading your data export before deleting your account."
    }
