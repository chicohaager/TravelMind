"""Tests for the cross-trip analytics summary."""

import datetime as dt

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.trip import Trip
from models.diary import DiaryEntry
from models.expense import Expense
from models.user import User


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession, test_user: User):
    trip = Trip(
        title="Lisbon", destination="Lisbon", owner_id=test_user.id,
        start_date=dt.datetime(2025, 6, 1), end_date=dt.datetime(2025, 6, 5),  # 5 days inclusive
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)

    db_session.add_all([
        DiaryEntry(title="D1", content="x", trip_id=trip.id, author_id=test_user.id),
        DiaryEntry(title="D2", content="y", trip_id=trip.id, author_id=test_user.id),
        Expense(trip_id=trip.id, title="Dinner", amount=40.0, currency="EUR",
                category="food", date=dt.date(2025, 6, 1)),
        Expense(trip_id=trip.id, title="Taxi", amount=20.0, currency="EUR",
                category="transport", date=dt.date(2025, 6, 2)),
        Expense(trip_id=trip.id, title="Souvenir", amount=15.0, currency="USD",
                category="other", date=dt.date(2025, 6, 3)),
    ])
    await db_session.commit()
    return trip


@pytest.mark.asyncio
async def test_summary_aggregates_activity_and_spend(client: AsyncClient, seeded, auth_headers):
    resp = await client.get("/api/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["trips"] == 1
    assert data["diary_entries"] == 2
    assert data["travel_days"] == 5  # 1 Jun .. 5 Jun inclusive
    assert data["primary_currency"] == "EUR"  # 60 EUR > 15 USD
    assert data["total_spend"] == 60.0
    assert data["spend_by_currency"] == {"EUR": 60.0, "USD": 15.0}

    cats = {c["category"]: c["amount"] for c in data["spend_by_category"]}
    assert cats == {"food": 40.0, "transport": 20.0}  # USD 'other' excluded (not primary currency)
    assert data["entries_by_trip"] == [{"label": "Lisbon", "count": 2}]
    assert data["trips_by_year"] == [{"label": "2025", "count": 1}]


@pytest.mark.asyncio
async def test_summary_empty_for_new_user(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["trips"] == 0 and data["photos"] == 0 and data["total_spend"] == 0.0


@pytest.mark.asyncio
async def test_summary_excludes_other_users_trips(client: AsyncClient, seeded, db_session):
    # A fresh, unrelated user sees nothing from the seeded owner's trip.
    user = User(username="eve", email="eve@example.com",
                hashed_password=User.hash_password("evepass12345"), is_active=True)
    db_session.add(user)
    await db_session.commit()
    login = await client.post(
        "/api/auth/login",
        data={"username": "eve", "password": "evepass12345"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    data = (await client.get("/api/analytics/summary", headers=headers)).json()
    assert data["trips"] == 0
