"""Tests for drag-and-drop reordering of a diary entry's photos."""

import io

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.trip import Trip
from models.user import User
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), (120, 160, 200)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def isolate_uploads(tmp_path, monkeypatch):
    import routes.diary as diary_routes
    import utils.images as images

    monkeypatch.setattr(diary_routes, "UPLOAD_DIR", tmp_path / "diary")
    monkeypatch.setattr(images, "UPLOADS_ROOT", tmp_path.resolve())


@pytest_asyncio.fixture
async def trip(db_session: AsyncSession, test_user: User) -> Trip:
    t = Trip(title="Porto", destination="Porto", owner_id=test_user.id)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


async def _entry_with_three_photos(client, trip_id, headers):
    entry_id = (
        await client.post(f"/api/diary/{trip_id}", json={"title": "Day 1", "content": "x"}, headers=headers)
    ).json()["id"]
    ids = []
    for _ in range(3):
        r = await client.post(
            f"/api/diary/{entry_id}/upload-photo",
            files={"file": ("p.jpg", _jpeg(), "image/jpeg")},
            headers=headers,
        )
        ids.append(r.json()["media"]["id"])
    return entry_id, ids


@pytest.mark.asyncio
async def test_reorder_persists_new_order(client: AsyncClient, trip, auth_headers):
    entry_id, ids = await _entry_with_three_photos(client, trip.id, auth_headers)
    reversed_ids = list(reversed(ids))

    resp = await client.patch(
        f"/api/diary/{entry_id}/photos/order",
        json={"media_ids": reversed_ids},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert [m["id"] for m in resp.json()] == reversed_ids

    # The diary listing reflects the new order too (relationship orders by order_index).
    listing = await client.get(f"/api/diary/{trip.id}", headers=auth_headers)
    entry = next(e for e in listing.json() if e["id"] == entry_id)
    assert [m["id"] for m in entry["media"]] == reversed_ids


@pytest.mark.asyncio
async def test_reorder_rejects_wrong_id_set(client: AsyncClient, trip, auth_headers):
    entry_id, ids = await _entry_with_three_photos(client, trip.id, auth_headers)

    # Missing one id.
    resp = await client.patch(
        f"/api/diary/{entry_id}/photos/order",
        json={"media_ids": ids[:2]},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Foreign id mixed in.
    resp = await client.patch(
        f"/api/diary/{entry_id}/photos/order",
        json={"media_ids": ids + [999999]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_owner_cannot_reorder(client: AsyncClient, trip, auth_headers, other_auth_headers):
    entry_id, ids = await _entry_with_three_photos(client, trip.id, auth_headers)
    resp = await client.patch(
        f"/api/diary/{entry_id}/photos/order",
        json={"media_ids": list(reversed(ids))},
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
