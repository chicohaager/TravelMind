"""
Tests for cross-entity search (SQLite/ILIKE path) — including user scoping.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.diary import DiaryEntry
from models.place import Place
from models.trip import Trip
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession, test_user: User):
    trip = Trip(
        title="Portugal Roadtrip", destination="Lisbon", description="Along the Atlantic coast", owner_id=test_user.id
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)

    db_session.add(
        DiaryEntry(
            trip_id=trip.id,
            author_id=test_user.id,
            title="Day 1",
            content="We ate amazing pasteis de nata in Belem",
            tags=[],
            photos=[],
        )
    )
    db_session.add(
        Place(
            trip_id=trip.id,
            name="Time Out Market",
            description="A famous food hall",
            latitude=38.7,
            longitude=-9.1,
            photos=[],
            tags=[],
        )
    )
    await db_session.commit()
    return trip


@pytest.mark.asyncio
async def test_search_finds_across_entities(client: AsyncClient, seeded, auth_headers):
    # Diary content
    r = await client.get("/api/search", params={"q": "pasteis"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert any(h["type"] == "diary" for h in body["results"])

    # Place name
    r = await client.get("/api/search", params={"q": "Time Out"}, headers=auth_headers)
    assert any(h["type"] == "place" and h["trip_id"] == seeded.id for h in r.json()["results"])

    # Trip destination
    r = await client.get("/api/search", params={"q": "Lisbon"}, headers=auth_headers)
    assert any(h["type"] == "trip" for h in r.json()["results"])


@pytest.mark.asyncio
async def test_short_query_returns_empty(client: AsyncClient, seeded, auth_headers):
    r = await client.get("/api/search", params={"q": "a"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_is_scoped_to_user(client: AsyncClient, db_session, seeded, auth_headers):
    # Another user's trip with a matching term must not leak.
    other = User(
        username="bob", email="bob@example.com", hashed_password=User.hash_password("bobpass123"), is_active=True
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    db_session.add(Trip(title="Secret Lisbon trip", destination="Lisbon", description="private", owner_id=other.id))
    await db_session.commit()

    r = await client.get("/api/search", params={"q": "Secret"}, headers=auth_headers)
    assert r.json()["total"] == 0
