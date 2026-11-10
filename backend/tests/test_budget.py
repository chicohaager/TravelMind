"""Tests for expense creation, focused on solo trips (no participants)."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.trip import Trip
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def trip(db_session: AsyncSession, test_user: User) -> Trip:
    t = Trip(title="Solo", destination="Porto", owner_id=test_user.id)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.mark.asyncio
async def test_solo_expense_without_paid_by_or_splits(client: AsyncClient, trip, auth_headers):
    """A trip with no participants can still record a simple expense."""
    resp = await client.post(
        f"/api/budget/{trip.id}/expenses",
        json={"title": "Hotel", "amount": 120.0, "category": "accommodation", "date": "2025-06-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["amount"] == 120.0
    assert body["paid_by"] is None

    listing = await client.get(f"/api/budget/{trip.id}/expenses", headers=auth_headers)
    assert listing.status_code == 200
    assert [e["title"] for e in listing.json()] == ["Hotel"]


@pytest.mark.asyncio
async def test_bogus_paid_by_still_rejected(client: AsyncClient, trip, auth_headers):
    resp = await client.post(
        f"/api/budget/{trip.id}/expenses",
        json={"title": "X", "amount": 10.0, "date": "2025-06-01", "paid_by": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404
