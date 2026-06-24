"""Tests for public read-only diary sharing.

Covers the security-critical contract: a share token only works while the trip
is public, disabling/regenerating revokes old links, the public endpoint needs
no auth, and the payload excludes private data.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.trip import Trip
from models.diary import DiaryEntry
from models.user import User


@pytest_asyncio.fixture
async def trip_with_entry(db_session: AsyncSession, test_user: User) -> Trip:
    t = Trip(title="Lisbon", destination="Lisbon", owner_id=test_user.id, budget=1500.0)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    db_session.add(DiaryEntry(title="Day 1", content="Arrived.", trip_id=t.id, author_id=test_user.id))
    await db_session.commit()
    return t


async def _publish(client, trip_id, headers, is_public=True, regenerate=False):
    resp = await client.patch(
        f"/api/trips/{trip_id}/publish",
        json={"is_public": is_public, "regenerate": regenerate},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_publish_mints_token_and_public_diary_is_readable_without_auth(
    client: AsyncClient, trip_with_entry, auth_headers
):
    body = await _publish(client, trip_with_entry.id, auth_headers)
    token = body["share_token"]
    assert body["is_public"] is True
    assert token and body["share_path"] == f"/share/{token}"

    # No Authorization header — must still work.
    resp = await client.get(f"/api/public/diary/{token}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Lisbon"
    assert [e["title"] for e in data["entries"]] == ["Day 1"]
    # Private data must not leak.
    assert "budget" not in data
    assert "owner_id" not in data
    assert "latitude" not in data["entries"][0]


@pytest.mark.asyncio
async def test_disabling_share_revokes_link(client: AsyncClient, trip_with_entry, auth_headers):
    token = (await _publish(client, trip_with_entry.id, auth_headers))["share_token"]
    assert (await client.get(f"/api/public/diary/{token}")).status_code == 200

    await _publish(client, trip_with_entry.id, auth_headers, is_public=False)
    assert (await client.get(f"/api/public/diary/{token}")).status_code == 404


@pytest.mark.asyncio
async def test_token_is_stable_across_toggle_but_regenerate_revokes(
    client: AsyncClient, trip_with_entry, auth_headers
):
    first = (await _publish(client, trip_with_entry.id, auth_headers))["share_token"]
    # Toggling off then on keeps the same token (stable public URL).
    await _publish(client, trip_with_entry.id, auth_headers, is_public=False)
    second = (await _publish(client, trip_with_entry.id, auth_headers))["share_token"]
    assert second == first

    # Regenerate mints a new token and the old one stops working.
    third = (await _publish(client, trip_with_entry.id, auth_headers, regenerate=True))["share_token"]
    assert third != first
    assert (await client.get(f"/api/public/diary/{first}")).status_code == 404
    assert (await client.get(f"/api/public/diary/{third}")).status_code == 200


@pytest.mark.asyncio
async def test_unknown_token_is_404(client: AsyncClient):
    assert (await client.get("/api/public/diary/does-not-exist")).status_code == 404


@pytest.mark.asyncio
async def test_non_owner_cannot_publish(client: AsyncClient, trip_with_entry, other_auth_headers):
    resp = await client.patch(
        f"/api/trips/{trip_with_entry.id}/publish",
        json={"is_public": True},
        headers=other_auth_headers,
    )
    assert resp.status_code in (403, 404)


@pytest_asyncio.fixture
async def other_auth_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    user = User(
        username="mallory",
        email="mallory@example.com",
        hashed_password=User.hash_password("mallorypass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    resp = await client.post(
        "/api/auth/login",
        data={"username": "mallory", "password": "mallorypass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
