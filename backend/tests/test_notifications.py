"""Tests for in-app notifications raised by trip-sharing events."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.trip import Trip
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def trip(db_session: AsyncSession, test_user: User) -> Trip:
    t = Trip(title="Lisbon", destination="Lisbon", owner_id=test_user.id)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        username="mallory",
        email="mallory@example.com",
        full_name="Mallory M",
        hashed_password=User.hash_password("mallorypass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _login(client, username, password):
    resp = await client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_invite_notifies_invitee(client: AsyncClient, trip, auth_headers, other_user):
    # Owner invites the other user.
    resp = await client.post(
        f"/api/trips/{trip.id}/share",
        json={"username_or_email": "mallory", "permission": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    other_headers = await _login(client, "mallory", "mallorypass123")
    notifs = (await client.get("/api/notifications", headers=other_headers)).json()
    assert len(notifs) == 1
    assert notifs[0]["type"] == "invite_received"
    assert notifs[0]["trip_id"] == trip.id
    assert notifs[0]["trip_title"] == "Lisbon"
    assert notifs[0]["is_read"] is False

    count = (await client.get("/api/notifications/unread-count", headers=other_headers)).json()
    assert count["count"] == 1


@pytest.mark.asyncio
async def test_accept_notifies_owner_and_mark_read_flow(client: AsyncClient, trip, auth_headers, other_user):
    await client.post(
        f"/api/trips/{trip.id}/share",
        json={"username_or_email": "mallory", "permission": "viewer"},
        headers=auth_headers,
    )
    other_headers = await _login(client, "mallory", "mallorypass123")
    await client.post(f"/api/trips/{trip.id}/share/accept", headers=other_headers)

    # Owner now has an invite_accepted notification.
    owner_notifs = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert [n["type"] for n in owner_notifs] == ["invite_accepted"]
    assert owner_notifs[0]["actor_name"] == "Mallory M"

    nid = owner_notifs[0]["id"]
    await client.patch(f"/api/notifications/{nid}/read", headers=auth_headers)
    assert (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["count"] == 0


@pytest.mark.asyncio
async def test_notifications_are_per_user(client: AsyncClient, trip, auth_headers, other_user):
    await client.post(
        f"/api/trips/{trip.id}/share",
        json={"username_or_email": "mallory", "permission": "viewer"},
        headers=auth_headers,
    )
    # The owner has no notifications yet (only the invitee does).
    assert (await client.get("/api/notifications", headers=auth_headers)).json() == []

    other_headers = await _login(client, "mallory", "mallorypass123")
    other_notifs = (await client.get("/api/notifications", headers=other_headers)).json()
    nid = other_notifs[0]["id"]

    # The owner cannot mark the invitee's notification read.
    resp = await client.patch(f"/api/notifications/{nid}/read", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, trip, auth_headers, other_user):
    await client.post(
        f"/api/trips/{trip.id}/share",
        json={"username_or_email": "mallory", "permission": "viewer"},
        headers=auth_headers,
    )
    other_headers = await _login(client, "mallory", "mallorypass123")
    assert (await client.post("/api/notifications/read-all", headers=other_headers)).json()["count"] == 0
    assert (await client.get("/api/notifications/unread-count", headers=other_headers)).json()["count"] == 0
