"""
Analytics Router

Cross-trip statistics for the current user's dashboard: activity counts (trips,
diary entries, photos, travel days) and spending (by category / currency),
aggregated over every trip the user can see.
"""

from collections import Counter
from typing import Dict, List

import structlog
from fastapi import APIRouter, Depends, Request
from models.database import get_db
from models.diary import DiaryEntry
from models.expense import Expense
from models.media import Media
from models.participant import InvitationStatus, Participant
from models.trip import Trip
from models.user import User
from pydantic import BaseModel
from routes.auth import get_current_active_user
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.rate_limits import RateLimits, limiter

logger = structlog.get_logger(__name__)
router = APIRouter()


class NamedCount(BaseModel):
    label: str
    count: int


class CategorySpend(BaseModel):
    category: str
    amount: float


class AnalyticsSummary(BaseModel):
    trips: int
    diary_entries: int
    photos: int
    travel_days: int
    primary_currency: str
    total_spend: float  # in the primary currency
    spend_by_currency: Dict[str, float]
    spend_by_category: List[CategorySpend]  # primary currency only
    photos_by_trip: List[NamedCount]
    entries_by_trip: List[NamedCount]
    trips_by_year: List[NamedCount]


async def _accessible_trip_ids(current_user: User, db: AsyncSession):
    """Trip ids the user can see: own + accepted-shared (superuser: all)."""
    if current_user.is_superuser:
        rows = await db.execute(select(Trip.id))
        return [r[0] for r in rows.all()]
    shared = await db.execute(
        select(Participant.trip_id).where(
            Participant.user_id == current_user.id,
            Participant.invitation_status == InvitationStatus.ACCEPTED.value,
        )
    )
    shared_ids = [r[0] for r in shared.all()]
    own = await db.execute(
        select(Trip.id).where(or_(Trip.owner_id == current_user.id, Trip.id.in_(shared_ids) if shared_ids else False))
    )
    return [r[0] for r in own.all()]


@router.get("/summary", response_model=AnalyticsSummary)
@limiter.limit(RateLimits.DIARY_LIST)
async def analytics_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Aggregate dashboard statistics across the user's accessible trips."""
    trip_ids = await _accessible_trip_ids(current_user, db)
    if not trip_ids:
        return AnalyticsSummary(
            trips=0,
            diary_entries=0,
            photos=0,
            travel_days=0,
            primary_currency="EUR",
            total_spend=0.0,
            spend_by_currency={},
            spend_by_category=[],
            photos_by_trip=[],
            entries_by_trip=[],
            trips_by_year=[],
        )

    trips = (await db.execute(select(Trip).where(Trip.id.in_(trip_ids)))).scalars().all()
    titles = {t.id: t.title for t in trips}

    # Travel days: inclusive span for trips with both dates.
    travel_days = 0
    year_counter = Counter()
    for t in trips:
        if t.start_date and t.end_date:
            travel_days += (t.end_date.date() - t.start_date.date()).days + 1
        if t.start_date:
            year_counter[str(t.start_date.year)] += 1

    diary_entries = (
        await db.execute(select(func.count()).select_from(DiaryEntry).where(DiaryEntry.trip_id.in_(trip_ids)))
    ).scalar() or 0

    photos = (
        await db.execute(select(func.count()).select_from(Media).where(Media.trip_id.in_(trip_ids)))
    ).scalar() or 0

    photos_per_trip = (
        await db.execute(select(Media.trip_id, func.count()).where(Media.trip_id.in_(trip_ids)).group_by(Media.trip_id))
    ).all()
    entries_per_trip = (
        await db.execute(
            select(DiaryEntry.trip_id, func.count())
            .where(DiaryEntry.trip_id.in_(trip_ids))
            .group_by(DiaryEntry.trip_id)
        )
    ).all()

    # Spending: by currency, and by category in the primary (most-used) currency.
    cur_rows = (
        await db.execute(
            select(Expense.currency, func.sum(Expense.amount))
            .where(Expense.trip_id.in_(trip_ids))
            .group_by(Expense.currency)
        )
    ).all()
    spend_by_currency = {cur or "EUR": round(amt or 0, 2) for cur, amt in cur_rows}
    primary_currency = max(spend_by_currency, key=spend_by_currency.get) if spend_by_currency else "EUR"

    cat_rows = (
        await db.execute(
            select(Expense.category, func.sum(Expense.amount))
            .where(Expense.trip_id.in_(trip_ids), Expense.currency == primary_currency)
            .group_by(Expense.category)
        )
    ).all()
    spend_by_category = sorted(
        [CategorySpend(category=c or "other", amount=round(a or 0, 2)) for c, a in cat_rows],
        key=lambda x: x.amount,
        reverse=True,
    )

    def top_named(rows, n=8):
        named = sorted(
            [NamedCount(label=titles.get(tid, "—"), count=cnt) for tid, cnt in rows],
            key=lambda x: x.count,
            reverse=True,
        )
        return named[:n]

    logger.info("analytics_summary", user_id=current_user.id, trips=len(trips))
    return AnalyticsSummary(
        trips=len(trips),
        diary_entries=diary_entries,
        photos=photos,
        travel_days=travel_days,
        primary_currency=primary_currency,
        total_spend=round(spend_by_currency.get(primary_currency, 0.0), 2),
        spend_by_currency=spend_by_currency,
        spend_by_category=spend_by_category,
        photos_by_trip=top_named(photos_per_trip),
        entries_by_trip=top_named(entries_per_trip),
        trips_by_year=[NamedCount(label=y, count=c) for y, c in sorted(year_counter.items())],
    )
