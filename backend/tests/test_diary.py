"""Tests for diary entry creation, focused on the entry_date tz handling.

``entry_date`` is a TIMESTAMP WITHOUT TIME ZONE column, so tz-aware values must
be coerced to naive UTC before storage (on real Postgres/asyncpg a tz-aware
value raises "can't subtract offset-naive and offset-aware datetimes").
"""

import datetime as dt

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.trip import Trip
from models.user import User
from routes.diary import _to_naive_utc
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def trip(db_session: AsyncSession, test_user: User) -> Trip:
    t = Trip(title="Oslo", destination="Oslo", owner_id=test_user.id)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


def test_to_naive_utc_converts_aware_to_naive_utc():
    aware = dt.datetime(2025, 6, 1, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=2)))
    naive = _to_naive_utc(aware)
    assert naive.tzinfo is None
    assert naive == dt.datetime(2025, 6, 1, 10, 0)  # +02:00 -> UTC


def test_to_naive_utc_passes_through_naive_and_none():
    assert _to_naive_utc(None) is None
    naive = dt.datetime(2025, 1, 1, 0, 0)
    assert _to_naive_utc(naive) is naive


@pytest.mark.asyncio
async def test_create_entry_accepts_tz_aware_entry_date(client: AsyncClient, trip, auth_headers):
    resp = await client.post(
        f"/api/diary/{trip.id}",
        json={"title": "Day 1", "content": "Arrived.", "entry_date": "2025-06-01T12:00:00+02:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    # Stored and returned as tz-naive UTC (12:00+02:00 -> 10:00).
    assert resp.json()["entry_date"] == "2025-06-01T10:00:00"


@pytest.mark.asyncio
async def test_create_entry_defaults_entry_date_when_missing(client: AsyncClient, trip, auth_headers):
    resp = await client.post(
        f"/api/diary/{trip.id}",
        json={"title": "Day 2", "content": "No date given."},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    # A default was applied and it is tz-naive (no offset suffix).
    entry_date = resp.json()["entry_date"]
    assert entry_date is not None
    assert "+" not in entry_date and not entry_date.endswith("Z")
