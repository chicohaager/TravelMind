"""
Tests for trip endpoints - including authorization and pagination
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models.trip import Trip
from models.user import User


@pytest_asyncio.fixture
async def test_trip(db_session: AsyncSession, test_user: User) -> Trip:
    """Create a test trip"""
    trip = Trip(
        title="Test Trip to Paris",
        destination="Paris",
        description="A wonderful trip",
        latitude=48.8566,
        longitude=2.3522,
        budget=1500.0,
        currency="EUR",
        interests=["culture", "food"],
        owner_id=test_user.id
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)
    return trip


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create another test user"""
    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=User.hash_password("otherpass123"),
        full_name="Other User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_auth_headers(client: AsyncClient, other_user: User) -> dict:
    """Get authorization headers for other user"""
    response = await client.post(
        "/api/auth/login",
        data={"username": "otheruser", "password": "otherpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_trip_success(client: AsyncClient, test_user, auth_headers):
    """Test creating a trip successfully"""
    response = await client.post(
        "/api/trips/",
        json={
            "title": "Summer in Barcelona",
            "destination": "Barcelona",
            "description": "Beach and culture",
            "latitude": 41.3851,
            "longitude": 2.1734,
            "budget": 2000.0,
            "currency": "EUR",
            "interests": ["beach", "culture"]
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Summer in Barcelona"
    assert data["destination"] == "Barcelona"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_trip_unauthenticated_demo_disabled(client: AsyncClient):
    """Test creating trip without auth when demo mode is disabled"""
    response = await client.post(
        "/api/trips/",
        json={
            "title": "Test Trip",
            "destination": "Berlin",
            "budget": 1000.0
        }
    )
    # Should fail if demo mode is disabled
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_trips_pagination(client: AsyncClient, test_user, auth_headers, db_session):
    """Test trip pagination"""
    # Create multiple trips
    for i in range(15):
        trip = Trip(
            title=f"Trip {i}",
            destination=f"City {i}",
            owner_id=test_user.id
        )
        db_session.add(trip)
    await db_session.commit()

    # Test first page
    response = await client.get("/api/trips/?skip=0&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10

    # Test second page
    response = await client.get("/api/trips/?skip=10&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5  # At least the remaining trips


@pytest.mark.asyncio
async def test_get_trip_success(client: AsyncClient, test_user, test_trip, auth_headers):
    """Test getting a specific trip"""
    response = await client.get(f"/api/trips/{test_trip.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_trip.id
    assert data["title"] == test_trip.title


@pytest.mark.asyncio
async def test_get_trip_unauthorized(client: AsyncClient, test_trip, other_auth_headers):
    """Test that users can't access trips they don't own"""
    response = await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_trip_not_found(client: AsyncClient, auth_headers):
    """Test getting non-existent trip"""
    response = await client.get("/api/trips/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_trip_success(client: AsyncClient, test_user, test_trip, auth_headers):
    """Test updating own trip"""
    response = await client.put(
        f"/api/trips/{test_trip.id}",
        json={"title": "Updated Trip Title", "budget": 2000.0},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Trip Title"
    assert data["budget"] == 2000.0
    assert data["destination"] == test_trip.destination  # Unchanged


@pytest.mark.asyncio
async def test_update_trip_unauthorized(client: AsyncClient, test_trip, other_auth_headers):
    """Test that users can't update trips they don't own"""
    response = await client.put(
        f"/api/trips/{test_trip.id}",
        json={"title": "Hacked Title"},
        headers=other_auth_headers
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_trip_no_auth(client: AsyncClient, test_trip):
    """Test updating trip without authentication"""
    response = await client.put(
        f"/api/trips/{test_trip.id}",
        json={"title": "Hacked Title"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_trip_success(client: AsyncClient, test_user, test_trip, auth_headers):
    """Test deleting own trip"""
    response = await client.delete(f"/api/trips/{test_trip.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify trip is deleted
    response = await client.get(f"/api/trips/{test_trip.id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_trip_unauthorized(client: AsyncClient, test_trip, other_auth_headers):
    """Test that users can't delete trips they don't own"""
    response = await client.delete(f"/api/trips/{test_trip.id}", headers=other_auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_trip_no_auth(client: AsyncClient, test_trip):
    """Test deleting trip without authentication"""
    response = await client.delete(f"/api/trips/{test_trip.id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_trip_summary(client: AsyncClient, test_user, test_trip, auth_headers):
    """Test getting trip summary"""
    response = await client.get(f"/api/trips/{test_trip.id}/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "trip_id" in data
    assert "total_places" in data
    assert "total_diary_entries" in data
    assert "total_cost" in data
    assert data["trip_id"] == test_trip.id


@pytest.mark.asyncio
async def test_user_can_only_see_own_trips(client: AsyncClient, test_user, other_user, test_trip, auth_headers, db_session):
    """Test that users can only see their own trips"""
    # Create a trip for other user
    other_trip = Trip(
        title="Other User's Trip",
        destination="Rome",
        owner_id=other_user.id
    )
    db_session.add(other_trip)
    await db_session.commit()

    # Get trips as test_user
    response = await client.get("/api/trips/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Should only see own trips
    trip_ids = [trip["id"] for trip in data]
    assert test_trip.id in trip_ids
    assert other_trip.id not in trip_ids
